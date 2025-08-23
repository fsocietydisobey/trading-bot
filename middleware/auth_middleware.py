from functools import wraps
from flask import request, jsonify
import jwt
from config.settings import settings  # use centralized settings

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
            secret = (settings.JWT_SECRET or settings.SECRET_KEY).strip()
            if not secret:
                return jsonify({'message': 'Server JWT secret not configured'}), 500

            # Optional issuer/audience checks (only enforced if configured)
            issuer = settings.JWT_ISSUER or None
            audience = settings.JWT_AUDIENCE or None

            data = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                issuer=issuer,
                audience=audience,
                options={"require": ["sub", "iat", "exp"]},
            )
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