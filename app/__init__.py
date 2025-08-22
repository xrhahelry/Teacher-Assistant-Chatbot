from flask import Flask
from config import Config
from flask_session import Session
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    Session(app) 

    from .routes import views 
    app.register_blueprint(views)

    return app