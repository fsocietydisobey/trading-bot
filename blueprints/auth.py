from flask import Blueprint, request, jsonify, current_app
from models.user import User
import jwt
import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from db.mongo import mongo
from middleware.auth_middleware import token_required  # Import the decorator

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()  # Get JSON data from the request
    if not data:
        return jsonify({'message': 'No JSON data provided'}), 400

    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password or not email:
        return jsonify({'message': 'Missing required fields'}), 400

    existing_user = User.find_by_username(username)
    if existing_user:
        return jsonify({'message': 'Username already exists'}), 409

    hashed_password = generate_password_hash(password)  # Hash the password
    new_user = User(username, hashed_password, email)
    new_user.save()

    return jsonify({'message': 'User registered successfully'}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()  # Get JSON data from the request
    if not data:
        return jsonify({'message': 'No JSON data provided'}), 400

    username = data.get('username')
    password = data.get('password')

    user = User.find_by_username(username)

    if user and check_password_hash(user.password, password):  # Check hashed password
        now = datetime.datetime.utcnow()
        ttl_minutes = int(current_app.config.get('JWT_ACCESS_TTL_MIN', 30))
        payload = {
            'sub': username,                 # subject (user identifier)
            'iat': now,                      # issued-at
            'exp': now + datetime.timedelta(minutes=ttl_minutes),  # expiration
            'jti': str(uuid.uuid4()),        # unique token id for revocation/auditing
            # Optional hardening:
            # 'iss': 'your-service-name',
            # 'aud': 'your-client-id-or-audience'
        }
        token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({'token': token}), 200
    return jsonify({'message': 'Invalid credentials'}), 401



@auth_bp.route('/protected', methods=['GET'])
@token_required
def protected(current_user):
    return jsonify({'message': f'This is a protected route for user: {current_user}'})