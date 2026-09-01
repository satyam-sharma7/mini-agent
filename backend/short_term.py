import os
import redis
import json
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

r = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    username="default",
    port=int(os.getenv('REDIS_PORT')),
    password=os.environ.get('REDIS_PASSWORD'),

    decode_responses=True
)

def add_to_short_term(session_id: str, role: str, content: str):
    """Add message to Redis short-term memory."""
    key = f"chat:short_term:{session_id}"
    message = {"role": role, "content": content}
    r.rpush(key, json.dumps(message))
    r.ltrim(key, -20, -1)  # Keep only last 20 messages
    r.expire(key, 3600)  # 1 hour TTL

def get_short_term(session_id: str) -> List[Dict[str, str]]:
    """Get all messages from Redis short-term memory."""
    key = f"chat:short_term:{session_id}"
    messages = r.lrange(key, 0, -1)
    return [json.loads(m) for m in messages]

def clear_short_term(session_id: str):
    """Clear Redis short-term memory for a session."""
    r.delete(f"chat:short_term:{session_id}")
