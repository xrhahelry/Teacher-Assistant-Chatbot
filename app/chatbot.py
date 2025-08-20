import google.generativeai as genai

def get_output(api_key, model_name, prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content([prompt])
    return response.text