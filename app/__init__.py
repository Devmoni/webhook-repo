import os
from flask import Flask
from app.webhook.routes import webhook
from app.extensions import mongo
from dotenv import load_dotenv

def create_app():
    # Load environment variables from .env file
    load_dotenv()
    
    app = Flask(__name__)
    
    # Get MongoDB URI from environment variable
    app.config["MONGO_URI"] = os.getenv("MONGO_URI")
    
    if not app.config["MONGO_URI"]:
        raise ValueError("MONGO_URI not found in environment variables. Make sure .env file exists with MONGO_URI.")

    mongo.init_app(app)
    app.register_blueprint(webhook)

    return app
