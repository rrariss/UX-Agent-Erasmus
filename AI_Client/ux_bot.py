import ollama

def evaluate_answer(user_input, target_metric):
    """
    A hidden LLM call that acts as our strict Guardrail.
    It returns True if the user actually answered the question, False otherwise.
    """
    eval_prompt = f"""
    You are a strict data evaluator. 
    The current usability metric we are testing is: {target_metric}.
    The user said: "{user_input}"
    
    Did the user provide relevant feedback regarding the metric? 
    If they went off-topic, said 'I don't know', or gave nonsense, answer NO.
    If they gave actual feedback, answer YES.
    Reply strictly with a single word: YES or NO.
    """
    
    try:
        # We don't need history for this, just a clean, single prompt
        response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': eval_prompt}])
        answer = response['message']['content'].strip().upper()
        
        # Strip out any punctuation the LLM might hallucinate
        if "YES" in answer:
            return True
        return False
    except:
        # If the LLM fails, default to moving forward so the app doesn't crash
        return True 

def run_ux_interview():
    metrics = ["Learnability", "Efficiency", "Error Prevention"]
    current_metric_idx = 0
    max_turns = 8 # Increased slightly to allow for follow-ups
    turn_count = 0

    system_context = """You are an empathetic UX researcher conducting a usability interview. 
    The product is the University of Ruse website. The user just tried to find their course schedule for the semester.
    Keep your questions brief, conversational, and focused ONLY on the current topic requested.
    Do NOT ask multiple questions at once."""

    messages = [{"role": "system", "content": system_context}]

    print("\n--- University UX Bot Initialized (Type 'exit' to quit) ---")
    
    first_question = "Hi! I saw you were looking for your course schedule on the university site. To start, how easy was it to figure out where you needed to click first?"
    print(f"Bot: {first_question}")
    messages.append({"role": "assistant", "content": first_question})

    while current_metric_idx < len(metrics) and turn_count < max_turns:
        user_input = input("\nYou: ")
        
        if user_input.lower() in ['exit', 'stop', 'quit']:
            print("Bot: Thanks for your time! Session closed.")
            break
            
        current_metric = metrics[current_metric_idx]
        
        # --- THE GUARDRAIL CHECK ---
        is_valid_answer = evaluate_answer(user_input, current_metric)
        
        if is_valid_answer:
            # User gave a good answer! Move the checklist forward.
            current_metric_idx += 1
            
            if current_metric_idx < len(metrics):
                next_metric = metrics[current_metric_idx]
                steering_prompt = f"\n\n[SYSTEM DIRECTIVE: The user answered perfectly. Acknowledge it, then ask a new question specifically evaluating the next metric: {next_metric}.]"
            else:
                # We finished the list
                messages.append({"role": "user", "content": user_input})
                print("\nBot: That's all the feedback I need. Thank you so much for helping us improve the site!")
                break
        else:
            # User talked about bananas. DO NOT move the checklist forward.
            next_metric = current_metric # Keep the target the same
            steering_prompt = f"\n\n[SYSTEM DIRECTIVE: The user's answer was off-topic or vague. Politely redirect them and ask the question about '{next_metric}' again in a different way.]"

        # ---------------------------

        # Combine input and hidden steering prompt
        combined_input_for_api = user_input + steering_prompt
        messages.append({"role": "user", "content": combined_input_for_api})
        
        try:
            response = ollama.chat(model='llama3', messages=messages)
            bot_reply = response['message']['content']
            
            print(f"\nBot: {bot_reply}")
            messages.append({"role": "assistant", "content": bot_reply})
            turn_count += 1
            
        except Exception as e:
            print(f"\n[Error connecting to Ollama: {e}]")
            break

if __name__ == "__main__":
    run_ux_interview()