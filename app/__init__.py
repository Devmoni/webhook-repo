import os
from flask import Flask
from app.webhook.routes import webhook
from app.extensions import mongo
from dotenv import load_dotenv

def create_app():
    app = Flask(__name__)
    
    # Direct MongoDB URL connection
    app.config["MONGO_URI"] = "mongodb+srv://demon:demon@cluster0.8fkmz.mongodb.net/webhook_db?retryWrites=true&w=majority&appName=Cluster0"

    mongo.init_app(app)
    app.register_blueprint(webhook)

    return app
