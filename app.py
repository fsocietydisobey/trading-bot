import logging
from flask import Flask
from blueprints.auth import auth_bp
from blueprints.data import data_bp
from db.mongo import mongo  # Import mongo
import os

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')  # Get SECRET_KEY from env
# app.config['MONGO_URI'] = "mongodb://mongo:27017/your_database"  # Set Mongo URI
app.config['MONGO_URI'] = os.environ.get('MONGO_URI')

# Initialize database connections
mongo.init_app(app)  # Initialize Flask-PyMongo

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(data_bp, url_prefix='/data')


@app.route('/')
def hello_world():
    logging.debug('Hello World!')
    return 'Hello World!'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
