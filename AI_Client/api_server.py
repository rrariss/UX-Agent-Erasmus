from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ollama
import uuid
import os
import chromadb
from chromadb.utils import embedding_functions

app = FastAPI(title="UX Agent API")

import sqlite3
from contextlib import asynccontextmanager


# Initialize RAG Connection
chroma_client = chromadb.PersistentClient(path="../rag_db") # Use ../ to avoid Live Server issues!
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
rag_collection = chroma_client.get_collection(name="ruse_website_map", embedding_function=sentence_transformer_ef)

# Initialize the SQLite Database
def init_db():
    conn = sqlite3.connect("../ux_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            sentiment TEXT,
            insight TEXT,
            raw_transcript TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Run the DB init when the server starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="UX Agent API", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all domains for prototyping
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active chat sessions (For prototype purposes)
active_sessions = {}

# --- Data Models (What the frontend will send to us) ---
class StartRequest(BaseModel):
    category: str

class ChatRequest(BaseModel):
    session_id: str
    user_message: str

# --- Helper Functions (From our previous prototype) ---
def evaluate_detail(user_input, category):
    eval_prompt = f"""You are a strict data evaluator. The category is: {category}.
    The user said: "{user_input}"
    
    CRITICAL RULES:
    1. POSITIVE PASS: If the user's feedback is generally positive, complimentary, or expresses satisfaction (e.g., "it was easy", "works great", "no issues"), answer YES immediately. Do not interrogate happy users.
    2. VAGUE NEGATIVE: If the feedback expresses frustration but is vague (e.g., "it sucks", "too hard", "confusing"), answer NO. We need more detail.
    3. SPECIFIC NEGATIVE: If the feedback is negative but mentions specific concrete issues (e.g., "the submit button is hidden", "404 error"), answer YES.
    
    Reply strictly with a single word: YES or NO."""
    
    try:
        response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': eval_prompt}])
        return "YES" in response['message']['content'].strip().upper()
    except:
        return True
    
def generate_ux_summary(category, history):
    system_prompt = """You are a senior UX Data Extraction AI. 
    Compress this interview transcript into a professional summary.
    
    CRITICAL INSTRUCTIONS:
    1. Do NOT include any introductory or concluding sentences (e.g., never say "Here is the summary").
    2. Do NOT use markdown bolding like **Sentiment**.
    3. You must output EXACTLY two lines in this precise format, and nothing else:
    
    - Sentiment: [Extract Sentiment]
    - Core Insight: [Your 1-2 sentence summary]"""
    
    transcript = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history if msg['role'] != 'system'])
    user_prompt = f"Category: {category}\nTranscript:\n{transcript}"
    
    try:
        response = ollama.chat(model='llama3', messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_prompt}])
        return response['message']['content'].strip()
    except Exception as e:
        return f"Error: {e}"

def save_to_db(category, history, ai_summary):
    transcript = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history if msg['role'] != 'system'])
    
    # Parse the strict 2-line output from the AI
    sentiment = "Neutral"
    insight = ai_summary
    
    try:
        lines = ai_summary.split('\n')
        for line in lines:
            if line.startswith("- Sentiment:"):
                sentiment = line.split(":", 1)[1].strip()
            elif line.startswith("- Core Insight:"):
                insight = line.split(":", 1)[1].strip()
    except Exception as e:
        print(f"Parsing error, saving raw summary: {e}")

    # Insert into SQLite
    conn = sqlite3.connect("../ux_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO feedback (category, sentiment, insight, raw_transcript)
        VALUES (?, ?, ?, ?)
    ''', (category, sentiment, insight, transcript))
    conn.commit()
    conn.close()
# --- API Endpoints ---

@app.post("/start")
async def start_session(request: StartRequest):
    """Initializes a new chat session when the user clicks a category."""
    session_id = str(uuid.uuid4())
    
    system_context = f"""You are an empathetic, warm UX researcher for the University of Ruse website.
    You are interviewing a user strictly about: {request.category}.
    CRITICAL RULES:
    1. Practice active listening: Validate their emotions first before asking a follow-up.
    2. Keep your tone human and conversational.
    3. Ask only ONE short clarifying question at a time."""
    
    first_prompt = f"Hi! I see you want to leave feedback regarding {request.category}. To start, could you tell me a bit about your experience with that?"
    
    # Store session state
    active_sessions[session_id] = {
        "category": request.category,
        "turn_count": 0,
        "max_turns": 3,
        "messages": [
            {"role": "system", "content": system_context},
            {"role": "assistant", "content": first_prompt}
        ]
    }
    
    return {"session_id": session_id, "bot_reply": first_prompt}

@app.post("/chat")
async def chat_interaction(request: ChatRequest):
    """Handles the back-and-forth conversation and the Guardrail checks."""
    if request.session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
        
    session = active_sessions[request.session_id]
    session["messages"].append({"role": "user", "content": request.user_message})
    
    # 1. Run Guardrail Evaluation
    is_detailed = evaluate_detail(request.user_message, session["category"])
    
# 2. Logic Branching
    if is_detailed or session["turn_count"] >= session["max_turns"]:
        # Dynamically generate an empathetic closing message
        close_prompt = f"The user just finished giving this feedback: '{request.user_message}'. Generate a short, 1-sentence empathetic closing message thanking them for this specific insight."
        closing_msg = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': close_prompt}])['message']['content'].strip()
        
        session["messages"].append({"role": "assistant", "content": closing_msg})
        
        # Run Synthesis and Save
        # Run Synthesis and Save to SQLite
        summary = generate_ux_summary(session["category"], session["messages"])
        save_to_db(session["category"], session["messages"], summary)
        
        del active_sessions[request.session_id]
        return {"bot_reply": closing_msg, "is_complete": True}
        
    else:
        # The user was vague. Ask for clarification, augmented by RAG!
        session["turn_count"] += 1
        
        # --- RAG SEARCH ---
        # Look up the 1 most relevant fact from our database based on the user's message
        rag_results = rag_collection.query(
            query_texts=[request.user_message],
            n_results=1
        )
        context_fact = rag_results['documents'][0][0] if rag_results['documents'] else "No specific site context found."
        # ------------------

        # Inject the context into the steering prompt
        steering_prompt = f"""\n\n[SYSTEM DIRECTIVE: The user's answer was slightly vague. Empathize with them, then ask them to clarify. 
        Use this verified fact about the website to make your question highly specific: "{context_fact}"]"""
        
        # API call
        api_messages = session["messages"][:-1] + [{"role": "user", "content": request.user_message + steering_prompt}]
        
        response = ollama.chat(model='llama3', messages=api_messages)
        bot_reply = response['message']['content']
        
        session["messages"].append({"role": "assistant", "content": bot_reply})
        return {"bot_reply": bot_reply, "is_complete": False}

@app.get("/api/dashboard-data")
async def get_dashboard_data():
    """Serves aggregated data and recent insights to the Product Owner Dashboard."""
    # Connect to the DB (using the ../ path to avoid Live Server refreshes!)
    conn = sqlite3.connect("../ux_database.db")
    conn.row_factory = sqlite3.Row # This lets us access columns by name
    cursor = conn.cursor()
    
# Query 1: Count ONLY negative feedback for the Problem Distribution Chart
    cursor.execute('''
        SELECT 
            category, 
            SUM(CASE WHEN sentiment LIKE '%Negative%' THEN 1 ELSE 0 END) as problem_count
        FROM feedback 
        GROUP BY category
        HAVING problem_count > 0
        ORDER BY problem_count DESC
    ''')
    chart_data = [dict(row) for row in cursor.fetchall()]
    
# Query 2: Get Insights ordered by Category Urgency (% Negative)
    cursor.execute('''
        WITH CategoryStats AS (
            SELECT 
                category,
                CAST(SUM(CASE WHEN sentiment LIKE '%Negative%' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as negative_ratio
            FROM feedback
            GROUP BY category
        )
        SELECT f.category, f.sentiment, f.insight, f.timestamp 
        FROM feedback f
        JOIN CategoryStats cs ON f.category = cs.category
        ORDER BY 
            cs.negative_ratio DESC, -- 1st: Bring categories with the highest % of negative reviews to the top
            CASE WHEN f.sentiment LIKE '%Negative%' THEN 1 ELSE 2 END, -- 2nd: Put the negative reviews first within that category
            f.timestamp DESC -- 3rd: Most recent first
    ''')
    insights = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "chart_data": chart_data,
        "insights": insights
    }