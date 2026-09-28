import ollama
import os

def evaluate_detail(user_input, category):
    """
    The Guardrail: A fast, 1-token check to determine if the user's feedback
    is specific enough, or if it requires a follow-up clarification.
    """
    eval_prompt = f"""You are a strict data evaluator. 
    The category is: {category}.
    The user said: "{user_input}"
    
    Is this feedback specific and detailed enough to be actionable for web developers? 
    If it is vague (e.g., "it was bad", "I don't know", "too many clicks" without explaining where), answer NO.
    If it mentions specific elements, feelings, or concrete issues, answer YES.
    Reply strictly with a single word: YES or NO."""
    
    try:
        response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': eval_prompt}])
        answer = response['message']['content'].strip().upper()
        if "YES" in answer:
            return True
        return False
    except:
        # Fallback to True so the app doesn't crash if the inference fails
        return True 

def generate_ux_summary(category, conversation_history):
    """
    The Synthesizer: Runs after the conversation ends to compress the chat 
    into a clean, structured summary for the database.
    """
    system_prompt = """You are a senior UX Research Assistant at the University of Ruse.
    Analyze this short interview transcript and compress it into a professional summary.
    Extract the core sentiment and the main actionable insight.
    Keep it under 3 sentences."""
    
    # Format the history into a readable transcript for the summarizer
    transcript = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" 
                            for msg in conversation_history 
                            if msg['role'] != 'system'])
    
    user_prompt = f"Category: {category}\nTranscript:\n{transcript}\n\nFormat as:\n- Sentiment: [Sentiment]\n- Core Insight: [Insight]"
    
    try:
        response = ollama.chat(model='llama3', messages=[
            {'role': 'system', 'content': system_prompt}, 
            {'role': 'user', 'content': user_prompt}
        ])
        return response['message']['content'].strip()
    except Exception as e:
        return f"Error running synthesis: {e}"

def save_to_file(category, conversation_history, summary):
    """
    Appends the full interaction and AI summary to the text database.
    """
    file_name = "university_ux_database.txt"
    
    # Rebuild transcript for saving
    transcript = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" 
                            for msg in conversation_history 
                            if msg['role'] != 'system'])
    
    with open(file_name, "a", encoding="utf-8") as f:
        f.write("="*50 + "\n")
        f.write(f"CATEGORY: {category}\n")
        f.write("RAW TRANSCRIPT:\n" + transcript + "\n\n")
        f.write("AI SYNTHESIS:\n" + summary + "\n")
        f.write("="*50 + "\n\n")

def chat_loop(category):
    """
    The main interactive loop for the selected category.
    """
    print(f"\n--- Starting {category} Interview (Type 'back' to quit) ---")
    
    system_context = f"""You are an empathetic, warm UX researcher for the University of Ruse website.
    You are interviewing a user strictly about: {category}.
    
    CRITICAL BEHAVIORAL RULES:
    1. Practice active listening: If the user expresses frustration, confusion, or annoyance, you MUST validate their emotions first before asking your next question (e.g., "I can completely understand why that would be frustrating," or "That sounds like a real hassle").
    2. Keep your tone conversational, supportive, and human. 
    3. Never sound like a robot reading a script. 
    4. Ask only ONE short, clarifying question at a time."""
    
    messages = [{"role": "system", "content": system_context}]
    
    # Ground the conversation immediately
    first_prompt = f"Hi! I see you want to leave feedback regarding {category}. To start, could you tell me a bit about your experience with that?"
    print(f"Bot: {first_prompt}")
    messages.append({"role": "assistant", "content": first_prompt})
    
    max_clarifications = 3
    turn_count = 0
    
    while turn_count < max_clarifications:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() in ['exit', 'stop', 'quit', 'back']:
            print("Bot: Exiting session. Returning to menu...")
            return 
            
        messages.append({"role": "user", "content": user_input})
        
        # Check if the user's answer was detailed enough
        is_detailed = evaluate_detail(user_input, category)
        
        if is_detailed:
            closing_msg = "That makes perfect sense. Thank you for the specific details, I've logged your feedback!"
            print(f"\nBot: {closing_msg}")
            messages.append({"role": "assistant", "content": closing_msg})
            break
        else:
            turn_count += 1
            if turn_count >= max_clarifications:
                closing_msg = "I appreciate your time! I'll log what we've discussed so far."
                print(f"\nBot: {closing_msg}")
                messages.append({"role": "assistant", "content": closing_msg})
                break
            
            # Force the AI to ask a clarifying question
            steering_prompt = f"\n\n[SYSTEM DIRECTIVE: The user's answer was slightly too vague. Politely ask them to clarify or provide a specific example regarding {category}.]"
            combined_input = user_input + steering_prompt
            
            # Prepare API messages (hiding the steering prompt from the permanent history)
            api_messages = messages[:-1] + [{"role": "user", "content": combined_input}]
            
            try:
                response = ollama.chat(model='llama3', messages=api_messages)
                bot_reply = response['message']['content']
                print(f"\nBot: {bot_reply}")
                messages.append({"role": "assistant", "content": bot_reply})
            except Exception as e:
                print(f"\n[Error: {e}]")
                break
                
    # Loop complete: Trigger Synthesis & Save
    print("\n[Synthesizing and saving data...]")
    summary = generate_ux_summary(category, messages)
    save_to_file(category, messages, summary)
    print(f"[SUCCESS] Chat logged to university_ux_database.txt\n")

def main_menu():
    categories = {
        "1": "Learnability (Navigation & First Clicks)",
        "2": "Efficiency (Speed & Task Completion)",
        "3": "Error Prevention (Broken Links & Confusion)"
    }
    
    while True:
        print("\n" + "#"*45)
        print("     UNIVERSITY OF RUSE - UX FEEDBACK")
        print("#"*45)
        print("Which area would you like to review?")
        for k, v in categories.items():
            print(f" [{k}] {v}")
        print(" [Q] Quit System")
        print("-" * 45)
        
        choice = input("Enter choice: ").strip().upper()
        
        if choice == 'Q':
            print("\nExiting system. Thank you!")
            break
            
        if choice in categories:
            category_name = categories[choice].split(" (")[0]
            chat_loop(category_name)
        else:
            print("\n[Invalid Selection. Please select 1, 2, 3, or Q.]")

if __name__ == "__main__":
    main_menu()