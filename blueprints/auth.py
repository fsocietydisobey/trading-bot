from flask import Blueprint, request, jsonify, current_app
from models.user import User
import jwt
import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from db.mongo import mongo
from middleware.auth_middleware import token_required  # Import the decorator
from config.settings import settings  # Centralized settings

auth_bp = Blueprint('auth', __name__)


# ... existing code ...
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

    # Basic validation
    # - email format (lightweight regex)
    # - password policy: min length 8, must contain a digit and a letter
    import re
    email_re = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    if not email_re.match(email or ""):
        return jsonify({'message': 'Invalid email format'}), 400
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return jsonify({'message': 'Password must be at least 8 characters and include letters and digits'}), 400

    existing_user = User.find_by_username(username)
    if existing_user:
        return jsonify({'message': 'Username already exists'}), 409

    hashed_password = generate_password_hash(password)  # Hash the password
    new_user = User(username, hashed_password, email)
    try:
        new_user.save()
    except ValueError:
        # Covers race condition with unique index
        return jsonify({'message': 'Username already exists'}), 409

    return jsonify({'message': 'User registered successfully'}), 201


# ... existing code ...
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
        # Prefer env-driven settings; fallback to defaults
        ttl_minutes = int(getattr(settings, 'JWT_ACCESS_TTL_MIN', 30) or 30)
        issuer = getattr(settings, 'JWT_ISSUER', '') or None
        audience = getattr(settings, 'JWT_AUDIENCE', '') or None
        secret = (getattr(settings, 'JWT_SECRET', '') or getattr(settings, 'SECRET_KEY', '')).strip()

        if not secret:
            return jsonify({'message': 'JWT secret not configured'}), 500

        payload = {
            'sub': username,  # subject (user identifier)
            'iat': now,  # issued-at
            'exp': now + datetime.timedelta(minutes=ttl_minutes),  # expiration
            'jti': str(uuid.uuid4()),  # unique token id for revocation/auditing
        }
        if issuer:
            payload['iss'] = issuer
        if audience:
            payload['aud'] = audience

        token = jwt.encode(payload, secret, algorithm='HS256')

        # Persist jti for potential revocation/auditing (middleware should enforce)
        try:
            mongo.db.token_jti.insert_one({
                'jti': payload['jti'],
                'sub': username,
                'exp': payload['exp']
            })
        except Exception:
            # Do not block login on auditing persistence failure
            pass

        return jsonify({'token': token}), 200
    return jsonify({'message': 'Invalid credentials'}), 401


# ... existing code ...
@auth_bp.route('/protected', methods=['GET'])
@token_required
def protected(current_user):
    return jsonify({'message': f'This is a protected route for user: {current_user}'})
