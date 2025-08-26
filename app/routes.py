from flask import Blueprint, render_template, current_app, request, session, redirect, url_for, flash
from .chatbot import get_output
import markdown, re
from .models import db, User, Chat, ChatThread

views = Blueprint("views", __name__)

@views.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        print("POST")
        fullname = request.form["fullname"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        academic_level = request.form["academic-level"]
        subject = request.form["default-subject"]

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("views.signup"))
        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for("views.signup"))

        user = User(
            username=username,
            fullname=fullname,
            email=email,
            default_academic_level=academic_level,
            default_subject=subject
        )
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
            Your Role:
            You are a professional teaching assistant.
            Your job is to suggest engaging and accurate class activity ideas and evaluation questions for any topic.
            I teach {subject} to {academic_level} students.
            The traits you should have is: 
            Classroom Manager, Knowledge Organizer, Creative Faciliator, Empathetic Mentor, Global Thinker, Tech Savvy Guide.
            You like to keep a professional setting while still being approachable.
            The format of your output should be:
            Always answer in full sentences, in structured format, and never give false information. Number the questions and activities. If possible use emojies where appropriate.
            I want you to generate:
            1. Three engaging in-class activities.
            2. Five practice questions with their corresponding answers.
            The activities should have a short description only: activity number:title , one line purpose, and a short description of how the activity is to be done in class.
            I may also ask you to change the activities or questions. So please make sure to remember the core topic and don't forget it.
        """

        # Alternate instructions when the user want to do normal conversations about the topic.
        altinstruction= f"""
            Your Role:
            You are a professional teaching assistant.
            Your job is to assist me in making my class as effective, engaging and accurate as possible.
            I teach {subject} to {academic_level} students.
            The traits you should have is: 
            Classroom Manager, Knowledge Organizer, Creative Faciliator, Empathetic Mentor, Global Thinker, Tech Savvy Guide.
            You like to keep a professional setting while still being approachable.
            The format of your output should be:
            Always answer in full sentences, in structured format, and never give false information. If possible use emojis
            I may also ask you to further refine the output. So please make sure to remember the core topic and don't forget it.
            You need to necessarily give class activities and evaluation questions, just do normal conversations.
        """

        # Create new chat thread
        thread = ChatThread(user_id=user_id, title=title, instruction=instruction, altinstruction=altinstruction)
        db.session.add(thread)
        db.session.commit()
        return redirect(url_for("views.chat", thread_id=thread.id))
    return render_template("onboarding.html")

@views.route("/chat")
def chat_latest():
    if not session.get("user_id"):
        return redirect(url_for("views.login"))
    
    user_id = session["user_id"]
    
    # Get the user's most recent chat thread
    latest_thread = ChatThread.query.filter_by(user_id=user_id).order_by(ChatThread.created_at.desc()).first()
    
    if latest_thread:
        # Redirect to the latest chat thread
        return redirect(url_for("views.chat", thread_id=latest_thread.id))
    else:
        # If no chat threads exist, redirect to onboarding to create the first one
        return redirect(url_for("views.onboarding"))

def preprocess_latex(text):
    # Convert $...$ blocks containing \begin{...} to $$...$$
    def block_replacer(match):
        content = match.group(1)
        if r"\begin{" in content:
            return f"$$ {content} $$"
        return f"${content}$"
    text = re.sub(r"\$(.+?)\$", block_replacer, text, flags=re.DOTALL)

    # Wrap bare \begin{pmatrix}...\end{pmatrix} blocks in $$...$$
    text = re.sub(r"(?<!\$)(\\begin{pmatrix}.*?\\end{pmatrix})(?!\$)", r"$$ \1 $$", text, flags=re.DOTALL)

    # Optionally, wrap other bare \begin{...}...\end{...} blocks in $$...$$
    text = re.sub(r"(?<!\$)(\\begin{[a-zA-Z]+}.*?\\end{[a-zA-Z]+})(?!\$)", r"$$ \1 $$", text, flags=re.DOTALL)

    return text

@views.route("/chat/<int:thread_id>", methods=["GET", "POST"])
def chat(thread_id):
    if not session.get("user_id"):
        return redirect(url_for("views.login"))
    user_id = session["user_id"]
    thread = ChatThread.query.filter_by(id=thread_id, user_id=user_id).first_or_404()
    user = User.query.get(user_id)
    chat_history = Chat.query.filter_by(thread_id=thread_id).order_by(Chat.timestamp).all()
    
    # Fetch user's chat threads for sidebar
    user_threads = ChatThread.query.filter_by(user_id=user_id).order_by(ChatThread.created_at.desc()).all()
    
    response = None

    if request.method == "POST":
        api_key = current_app.config["GEMINI_KEY"]
        model_name = current_app.config["GM_FLASH2"]
        user_input = request.form.get("user_input")
        choice = request.form.get("choice")

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
        if choice == None:
            instruction = thread.altinstruction
        else:
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
            # processed_message = preprocess_latex(msg.message)
            rendered_history.append({"sender": "bot", "message": markdown.markdown(msg.message, extensions=['nl2br', "fenced_code", "tables", "sane_lists"])})
        else:
            rendered_history.append({"sender": "user", "message": msg.message})

    return render_template("chat.html", response=response, chat_history=rendered_history, thread=thread, user=user, threads=user_threads)
