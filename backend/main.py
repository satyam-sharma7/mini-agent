import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import uuid
import asyncio
from sqlalchemy.orm import relationship
from sqlalchemy import String, ForeignKey
from sqlalchemy import String, TEXT, select, exists
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.exc import IntegrityError
import bcrypt
from typing import List, Dict, Any


from backend.auth import create_access_token, hash_password, verify_password, verify_token
from backend.schemas import LoginRequest, SignupRequest, TokenResponse, SessionResponse, MessageResponse, ChatRequest, ChatResponse
from backend.short_term import get_short_term, add_to_short_term
from src.agents.react import call_agent


load_dotenv()
app = FastAPI()

ALGORITHM = "HS256"
DATABASE_URL = os.environ.get("POSTGRES_URL")


async def get_current_user_id(authorization: str = Header(...)) -> str:
    token = authorization.replace("Bearer ", "")
    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_login: Mapped[datetime | None] = mapped_column(nullable=True)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    session: Mapped["Session"] = relationship(back_populates="messages")


async_engine = create_async_engine(url = DATABASE_URL, pool_size=10, max_overflow=20)
AsyncSessionFactory = async_sessionmaker(bind=async_engine, expire_on_commit=False)



async def get_db():
    async with async_engine.begin() as conn:
        # Avoid drop_all in a real production environment!
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)  # creates tables

    async with AsyncSessionFactory() as session:
        yield session


@app.post("/sing-up", response_model=TokenResponse)
async def create_user(req:LoginRequest, db: AsyncSession = Depends(get_db)):
    hash_pass = hash_password(req.password)
    user = User(email=req.email, hashed_password=hash_pass)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "Email already exists")
    # return user
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)

@app.post("/login", response_model=TokenResponse)
async def user_login(data:SignupRequest):
    async with AsyncSessionFactory() as session:
        query = select(exists().where(User.email == data.email))
        result = (await session.execute(query)).scalar()

    if result:
        query = select(User).where(User.email == data.email)
        user = (await session.execute(query)).scalar_one()
        if verify_password(data.password, user.hashed_password):
            token = create_access_token(str(user.id))
            return TokenResponse(access_token=token)
        else:
            raise HTTPException(401, "Wrong Password.")
    else:
        raise HTTPException(404, "Account do not exist.")


@app.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Session)
        .where(Session.user_id == uuid.UUID(user_id))
        .order_by(Session.updated_at.desc())
    )

    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "updated_at": s.updated_at
        }
        for s in sessions
    ]
    
@app.post("/sessions", response_model=dict)
async def create_session(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    session = Session(user_id=uuid.UUID(user_id), title="New Chat")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {"session_id": str(session.id)}


@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):    
    # Verify ownership
    query = select(Session).where(Session.id == session_id, Session.user_id == uuid.UUID(user_id))
    result = await db.execute(query)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=403, detail="Not your session")

    await db.delete(session)
    await db.commit()

    # Clear Redis cache
    # clear_short_term(str(session_id))

    return {"status": "deleted"}

@app.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Verify ownership
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == uuid.UUID(user_id)
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not your session")

    # Get messages
    result = await db.execute(
        select(Message)
        .where(Message.session_id == uuid.UUID(session_id),)
        .order_by(uuid.UUID(Message.created_at.asc()))
    )

    messages = result.scalars().all()
    return [
        {
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at
        } for m in messages
    ]


@app.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Verify session ownership
    result = await db.execute(
        select(Session).where(Session.id == req.session_id, Session.user_id == uuid.UUID(user_id))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=403, detail="Not your session")

    short_term_memory = get_short_term(str(req.session_id))
    print(short_term_memory)
    #llm_call
    full_response = ""
    try:
        # 1. Call LLM API with streaming enabled
        response_stream = call_agent(req.message, short_term_memory, str(req.session_id))

        # 2. Loop through incoming tokens from LLM
        async for token in response_stream:
            if token:
                full_response += token
                yield token

        print(full_response)
        # Save messages to database
        db.add(Message(
            session_id=req.session_id,
            role="user",
            content=req.message
        ))
        db.add(Message(
            session_id=req.session_id,
            role="assistant",
            content=full_response
        ))
        await db.commit()

        # Update short-term memory
        add_to_short_term(str(req.session_id), "user", req.message)
        add_to_short_term(str(req.session_id), "assistant", full_response)

        # Update session timestamp
        session.updated_at = datetime.utcnow()
        await db.commit()

    except Exception as e:
        yield f"\n[Error generating response: {str(e)}]"



