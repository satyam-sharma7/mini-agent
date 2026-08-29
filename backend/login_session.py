import jwt
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY")  # production me env variable se aayega
ALGORITHM = "HS256"

def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,  # "subject" — yaha user ka UUID jayega
        "exp": datetime.now(timezone.utc) + timedelta(seconds=10)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]  # user_id nikal aaya
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

