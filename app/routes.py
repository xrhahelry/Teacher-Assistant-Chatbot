from flask import Blueprint, render_template, current_app, request, session, redirect, url_for, flash
from .chatbot import get_output
import markdown
from .models import db, User, Chat, ChatThread

views = Blueprint("views", __name__)

@views.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("views.signup"))
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.")
        return redirect(url_for("views.login"))
    return render_template("signup.html")

@views.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Logged in successfully!")
            return redirect(url_for("views.home"))
        flash("Invalid credentials")
    return render_template("login.html")

@views.route("/logout")
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("views.home"))


@views.route("/")
def home():
    return render_template("home.html")

@views.route("/tutorial ")
def tutorial():
    return render_template("tutorial.html")

@views.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    if not session.get("user_id"):
        return redirect(url_for("views.login"))
    if request.method == 'POST':
        title = request.form.get("chat_title")
        academic_level = request.form.get("academic_level")
        subject = request.form.get("subject")
        user_id = session["user_id"]

        # Generate instruction using academic_level and subject
        instruction = f"""
            You are a professional teaching assistant.
            Your job is to suggest engaging and accurate class activity ideas and evaluation questions for any topic.
            Always answer in full sentences, in structured format, and never give false information.
            You like to keep a professional setting while still being approachable.
            I teach {subject} to {academic_level} students.
            I want you to generate:
            1. Three engaging in-class activities.
            2. Five practice questions with their corresponding answers.
            The activities should have a short description only: title, one line purpose, and a short description of how the activity is to be done in class.
            I may also ask you to change the activities or questions. So please make sure to remember the core topic and don't forget it.
        """

        # Create new chat thread
        thread = ChatThread(user_id=user_id, title=title, instruction=instruction)
        db.session.add(thread)
        db.session.commit()
        return redirect(url_for("views.chat", thread_id=thread.id))
    return render_template("onboarding.html")

@views.route("/history", methods=["GET", "POST"])
def history():
    if not session.get("user_id"):
        return redirect(url_for("views.login"))
    user_id = session["user_id"]

    if request.method == "POST":
        title = request.form.get("title")
        if title:
            thread = ChatThread(user_id=session["user_id"], title=title)
            db.session.add(thread)
            db.session.commit()
            return redirect(url_for("views.chat", thread_id=thread.id))

    user_threads = ChatThread.query.filter_by(user_id=session["user_id"]).order_by(ChatThread.created_at.desc()).all()
    return render_template("history.html", threads=user_threads)

@views.route("/chat/<int:thread_id>", methods=["GET", "POST"])
def chat(thread_id):
    if not session.get("user_id"):
        return redirect(url_for("views.login"))
    user_id = session["user_id"]
    thread = ChatThread.query.filter_by(id=thread_id, user_id=user_id).first_or_404()
    user = User.query.get(user_id)
    chat_history = Chat.query.filter_by(thread_id=thread_id).order_by(Chat.timestamp).all()
    response = None

    if request.method == "POST":
        api_key = current_app.config["GEMINI_KEY"]
        model_name = current_app.config["GM_FLASH2"]
        user_input = request.form.get("user_input")

        # Save user message
        user_msg = Chat(thread_id=thread_id, user_id=user_id, message=user_input, sender="user")
        db.session.add(user_msg)
        db.session.commit()

        # Build context from chat_history + new user message
        context = ""
        for msg in chat_history + [user_msg]:
            sender = "You" if msg.sender == "user" else "Bot"
            context += f"{sender}: {msg.message}\n"

        # Use instruction from thread and name from user
        instruction = thread.instruction
        name = user.username

        prompt = f"""
            {instruction}
            Teacher's name: {name}
            Here is our previous conversation:
            {context}

            What I asked you:
            {user_input}
        """
        response = get_output(api_key, model_name, prompt)
        response_html = markdown.markdown(response)

        # Save bot response
        bot_msg = Chat(thread_id=thread_id, user_id=user_id, message=response, sender="bot")
        db.session.add(bot_msg)
        db.session.commit()

        # Reload chat history including new messages
        chat_history = Chat.query.filter_by(thread_id=thread_id).order_by(Chat.timestamp).all()

    # Prepare chat_history for template (render markdown for bot)
    rendered_history = []
    for msg in chat_history:
        if msg.sender == "bot":
            rendered_history.append({"sender": "bot", "message": markdown.markdown(msg.message)})
        else:
            rendered_history.append({"sender": "user", "message": msg.message})

    return render_template("chat.html", response=response, chat_history=rendered_history, thread=thread, user=user)
