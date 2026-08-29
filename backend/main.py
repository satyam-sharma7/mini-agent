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

from backend.login_session import create_access_token, verify_token


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


class NewUser(BaseModel):
    email: str
    password: str

@app.post("/sing-up")
async def create_user(data:NewUser, db: AsyncSession = Depends(get_db)):
    salt = bcrypt.gensalt()  # random salt generate hota hai
    hash_pass = str(bcrypt.hashpw(bytes(data.password, encoding='utf-8'), salt), encoding='utf-8')

    user = User(email=data.email, hashed_password=hash_pass)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "Email already exists")
    # return user
    return {"status":"Account Created Please Login."}

@app.post("/login")
async def user_login(data:NewUser):
    async with AsyncSessionFactory() as session:
        query = select(exists().where(User.email == data.email))
        result = (await session.execute(query)).scalar()

    if result:
        query = select(User).where(User.email == data.email)
        result = (await session.execute(query)).scalar_one()
        hash_pass = result.hashed_password
        id = str(result.id)
        if bcrypt.checkpw(bytes(data.password, 'utf-8'), bytes(hash_pass, 'utf-8')):
            access_token = create_access_token(id)
            return {"Status":"Correct Password", "access_token":create_access_token(id)}
        else:
            raise HTTPException(401, "Wrong Password.")
    else:
        raise HTTPException(404, "Account do not exist.")
