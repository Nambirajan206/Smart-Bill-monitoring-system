from flask import Flask
from flask_cors import CORS
from models import db
from routes import register_routes
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///electricity_dept.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False  # Set to True for debugging SQL queries
    
    # Google Drive configuration
    app.config['GOOGLE_DRIVE_FOLDER_ID'] = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')

    # Initialize database
    db.init_app(app)

    # Create tables
    with app.app_context():
        db.create_all()

    # Register routes
    register_routes(app)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000, host='0.0.0.0')
