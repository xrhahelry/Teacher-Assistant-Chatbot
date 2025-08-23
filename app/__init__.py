from flask import Flask
from config import Config
from flask_session import Session
from .models import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    Session(app)

    with app.app_context():
        db.create_all()

    from .routes import views
    app.register_blueprint(views)

    return app