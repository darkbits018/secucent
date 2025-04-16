import jwt
import os
# Function to verify JWT
def verify_token(token):
    try:
        secret_key = os.environ.get('APP_SECRET')
        # Decode and verify the JWT token
        decoded_token = jwt.decode(token, secret_key, algorithms=['HS256'])
        return decoded_token, None
    except jwt.ExpiredSignatureError:
        return None, "Token has expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"