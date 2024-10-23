import jwt
from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta

SECRET_KEY = ""

def generate_token(service_name):
    payload = {
        "service": service_name,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["service"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token faltante"}), 401
        service = verify_token(token)
        if not service:
            return jsonify({"error": "Token inválido"}), 401
        return f(*args, **kwargs)
    return decorated