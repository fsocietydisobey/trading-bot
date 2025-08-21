from functools import wraps
from flask import request, jsonify, current_app
import jwt

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Extract token from "Bearer <token>"
            except IndexError:
                return jsonify({'message': 'Invalid token format'}), 401

        if not token:
            return jsonify({'message': 'Token is missing'}), 401

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            # Extract standard claims
            token_sub = data.get('sub')   # subject (user id/username)
            token_jti = data.get('jti')   # unique token id
            # Optional: check revocation/blacklist using token_jti
            # if is_token_revoked(token_jti):
            #     return jsonify({'message': 'Token has been revoked'}), 401
            if not token_sub:
                return jsonify({'message': 'Invalid token payload'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'message': f'Something went wrong: {str(e)}'}), 500

        return f(token_sub, *args, **kwargs)  # Pass subject (user id/username) to the route

    return decorated