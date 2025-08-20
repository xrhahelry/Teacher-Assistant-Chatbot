from flask import Blueprint, render_template, current_app, request, session
from .chatbot import get_output
import markdown

views = Blueprint("views", __name__)

@views.route("/")
def home():
    return render_template("index.html")

@views.route("/chat", methods=["GET", "POST"])
def chat():
    if "chat_history" not in session:
        session["chat_history"] = []

    response = None
    if request.method == "POST":
        print(session["chat_history"])
        api_key = current_app.config["GEMINI_KEY"]
        model_name = current_app.config["GM_FLASH2"]
        user_input = request.form.get("user_input")

        # Add user message to history
        session["chat_history"].append({
            "sender": "user",
            "message": user_input,
            "raw": user_input  # Store raw text for context
        })

        # Build context from all previous exchanges (user and bot)
        context = ""
        for msg in session["chat_history"]:
            sender = "You" if msg["sender"] == "user" else "Bot"
            context += f"{sender}: {msg['raw']}\n"

        name = "Sujal Bajracharya"
        subject = "Science"
        grade = "Grade 12"
        prompt = f"""
            You are a professional teaching assistant. 
            Your job is to suggest me engaging and accurate class activity ideas and evaluation questions for any topic.
            Always answer in full sentences, in structured format, and never give false information.
            You like to keep a professional setting while still being approchable. 
            My name is {name}. I teach {subject} to {grade} students.
            I want you to generate:
            1. Three engaging in-class activities.
            2. Five practice questions with their corresponding answers.
            I want the activities to have a short description only. Title, one line purpose and a short description of how the activity is to be done in class.
            I may also ask you to change the activities or questions. So please make sure to remember the core topic and don't forget it.
            Here is our previous conversation:
            {context}

            What I asked you:
            {user_input}
        """
        response = get_output(api_key, model_name, prompt)
        response_html = markdown.markdown(response)
        # Store both HTML and raw text for bot message
        session["chat_history"].append({
            "sender": "bot",
            "message": response_html,
            "raw": response
        })
    return render_template("chat.html", response=response, chat_history=session.get("chat_history", []))
