from pydantic import BaseModel
import uuid
from datetime import datetime

class SignupRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ChatRequest(BaseModel):
    message: str
    session_id: uuid.UUID

class ChatResponse(BaseModel):
    response: str

class SessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    updated_at: datetime

class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime
