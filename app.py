from flask import Flask
from flask_cors import CORS
from models import db
from routes import register_routes

def create_app():
    app = Flask(__name__)
    CORS(app)

   
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///electricity_dept.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False  # Set to True for debugging SQL queries

   
    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000, host='0.0.0.0')