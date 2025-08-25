import jwt
from config import JWT_SECRET_KEY

def generate_jwt_token(object:dict) -> str:
    return jwt.encode(object, JWT_SECRET_KEY, algorithm="HS256")

def decode_jwt_token(token:str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}