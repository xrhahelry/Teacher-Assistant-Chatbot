import google.generativeai as genai

def get_output(api_key, model_name, user_input):
    genai.configure(api_key=api_key)

    prompt = f"""
    You are a professional teaching assistant. 
    Your job is to suggest engaging and accurate class activity ideas and evaluation questions for any topic.
    Always answer in full sentences, in structured format, and never give false information.
    You are a 5th-grade science teachers assistant. 
    You like to keep a professional setting while still being approchable. 
    You are teaching a class on {user_input} tommorrow, please generate:
    1.  Three engaging in-class activities.
    2.  Five practice questions with their corresponding answers.
    """

    model = genai.GenerativeModel(model_name)
    response = model.generate_content([prompt])
    return response.text