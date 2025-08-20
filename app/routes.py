from flask import Blueprint, render_template, current_app, request
from .chatbot import get_output

# create a blueprint named "views"
views = Blueprint("views", __name__)

@views.route("/")
def home():
    return render_template("index.html")

@views.route("/chat", methods=["GET", "POST"])
def chat():
    response = None
    if request.method == "POST":
        api_key = current_app.config["GEMINI_KEY"]
        model_name = current_app.config["GM_FLASH"]
        user_input = request.form.get("user_input")
        response = get_output(api_key, model_name, user_input)
    return render_template("chat.html", response=response)
