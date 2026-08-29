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
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
import bcrypt



load_dotenv()
app = FastAPI()

ALGORITHM = "HS256"
DATABASE_URL = os.environ.get("POSTGRES_URL")

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
    # async with async_engine.begin() as conn:
    #     # Avoid drop_all in a real production environment!
    #     await conn.run_sync(Base.metadata.drop_all)
    #     await conn.run_sync(Base.metadata.create_all)  # creates tables

    async with AsyncSessionFactory() as session:
        yield session



async def display_users_table():
    async with AsyncSessionFactory() as session:
        # Build a select query
        query = select(User).where(User.email == "satyam77876@gmail.com")
        result = await session.execute(query)

    print(type(str(result.scalar_one().id)))

asyncio.run(display_users_table())
