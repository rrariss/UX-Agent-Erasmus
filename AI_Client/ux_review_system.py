import ollama
import os

def generate_ux_summary(category, user_feedback):
    """
    Task 2 & 3 Combined for Prototype: Sanitizes the raw text, 
    extracts key pain points, and formats it for the product owner.
    """
    # Optimized, hyper-specific system prompt
    system_prompt = """You are a senior UX Research Assistant at the University of Ruse. 
    Your task is to analyze raw student feedback regarding the university website and compress it into a highly professional, actionable summary for the web development team.
    
    CRITICAL INSTRUCTIONS:
    1. Identify the core problem or success mentioned.
    2. Extract the student's implicit emotional sentiment (e.g., Frustrated, Satisfied, Confused).
    3. If the feedback is completely unrelated nonsense, off-topic, or spam, flag it strictly as [SPAM/INVALID].
    4. Keep the summary under 3 sentences. Do not use generic filler words."""

    user_prompt = f"""
    Target Web Category: {category}
    Raw Student Feedback: "{user_feedback}"
    
    Provide the summary in this exact format:
    - Sentiment: [Extracted Sentiment]
    - Core Insight: [Brief summary of the issue or praise]
    """

    try:
        response = ollama.chat(
            model='llama3', 
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"Error running inference: {e}"

def save_to_file(category, raw_text, summary):
    """
    Saves the structured feedback to a local txt file database.
    """
    file_name = "university_ux_database.txt"
    with open(file_name, "a", encoding="utf-8") as f:
        f.write("="*50 + "\n")
        f.write(f"CATEGORY: {category}\n")
        f.write(f"RAW USER INPUT: {raw_text}\n")
        f.write(f"AI SYNTHESIS:\n{summary}\n")
        f.write("="*50 + "\n\n")

def main_menu():
    categories = {
        "1": "Learnability (How easy it is to find where to click first)",
        "2": "Efficiency (How fast it is to find schedules or grades)",
        "3": "Error Prevention & Interface (Broken links, bad colors, confusing text)"
    }

    while True:
        print("\n" + "#"*40)
        print("     UNIVERSITY OF RUSE - UX FEEDBACK")
        print("#"*40)
        print("Select a category you want to leave a review for:")
        for key, value in categories.items():
            print(f" [{key}] {value}")
        print(" [Q] Quit System")
        print("-" * 40)
        
        choice = input("Enter choice: ").strip()

        if choice.lower() == 'q':
            print("\nExiting system. Thank you!")
            break
        
        if choice in categories:
            selected_category = categories[choice].split(" (")[0] # Extracts just the metric name
            
            print(f"\n--- Reviewing: {selected_category} ---")
            print("Type your feedback below. (Or type 'BACK' to return to the main menu without saving)")
            user_feedback = input("\nYour Review: ").strip()

            if user_feedback.upper() == "BACK":
                print("\nReturned to main menu.")
                continue
                
            if not user_feedback:
                print("\n[Error: Feedback cannot be empty!]")
                continue

            print("\nProcessing your feedback with Llama 3...")
            
            # Run the task architecture
            ai_summary = generate_ux_summary(selected_category, user_feedback)
            
            # Save the result
            save_to_file(selected_category, user_feedback, ai_summary)
            
            print("\n[SUCCESS] Feedback saved to database!")
            print(f"\nPreview of what the Product Owner sees:\n{ai_summary}")
            
            # Loop continues automatically, acting as your natural "Back" mechanics
            input("\nPress Enter to submit another review...")
        else:
            print("\n[Invalid Selection. Please select 1, 2, 3, or Q.]")

if __name__ == "__main__":
    main_menu()