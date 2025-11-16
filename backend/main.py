from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import enum
import jwt
from datetime import datetime, timedelta
import uuid
from typing import List, Optional
import os
from pydantic import BaseModel

# Database setup
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/gymassistant"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security
security = HTTPBearer()
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"

app = FastAPI(title="GymAssistant Pro API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class UserRole(str, enum.Enum):
    member = "member"
    coach = "coach"
    admin = "admin"

class UserStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class TrainingGroup(str, enum.Enum):
    muscle_gain = "muscle_gain"
    fat_loss = "fat_loss"
    maintenance = "maintenance"

class MessageType(str, enum.Enum):
    text = "text"
    image = "image"
    system = "system"
    broadcast = "broadcast"

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    name = Column(String)
    role = Column(SQLEnum(UserRole), default=UserRole.member)
    status = Column(SQLEnum(UserStatus), default=UserStatus.pending)
    training_group = Column(SQLEnum(TrainingGroup), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    gym_id = Column(String)  # For multi-tenancy

class TrainingProgram(Base):
    __tablename__ = "training_programs"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    description = Column(Text)
    date = Column(DateTime)
    exercises = Column(Text)  # JSON string
    pdf_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    gym_id = Column(String)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True, index=True)
    sender_id = Column(String)
    sender_name = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(SQLEnum(MessageType), default=MessageType.text)
    gym_id = Column(String)

class GymEntry(Base):
    __tablename__ = "gym_entries"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String)
    entry_time = Column(DateTime)
    exit_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # in minutes
    gym_id = Column(String)

class Supplement(Base):
    __tablename__ = "supplements"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text)
    price = Column(Integer)
    image_url = Column(String, nullable=True)
    gym_id = Column(String)

class Gym(Base):
    __tablename__ = "gyms"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    logo = Column(String)
    primary_color = Column(String)
    secondary_color = Column(String)
    capacity = Column(Integer)
    entry_qr = Column(String)
    exit_qr = Column(String)
    subdomain = Column(String, unique=True)

# Pydantic Models
class UserCreate(BaseModel):
    phone_number: str
    name: str

class UserResponse(BaseModel):
    id: str
    phone_number: str
    name: str
    role: UserRole
    status: UserStatus
    training_group: Optional[TrainingGroup]
    created_at: datetime

    class Config:
        from_attributes = True

class TrainingProgramCreate(BaseModel):
    title: str
    description: str
    date: datetime
    exercises: str
    pdf_url: Optional[str] = None
    image_url: Optional[str] = None

class ChatMessageCreate(BaseModel):
    message: str
    type: MessageType = MessageType.text

class GymEntryCreate(BaseModel):
    user_id: str
    entry_time: datetime

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Routes
@app.post("/api/auth/request-verification")
async def request_verification(phone_number: str, db: Session = Depends(get_db)):
    # In production, integrate with SMS service
    return {"message": "Verification code sent", "code": "123456"}  # Demo code

@app.post("/api/auth/verify")
async def verify_code(phone_number: str, code: str, db: Session = Depends(get_db)):
    # Verify code (in production, use proper verification)
    if code != "123456":
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        # Create new user
        user = User(
            id=str(uuid.uuid4()),
            phone_number=phone_number,
            name="کاربر جدید",
            status=UserStatus.pending
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Create JWT token
    token_data = {"sub": user.id}
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@app.get("/api/users/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/api/training-programs")
async def get_training_programs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    programs = db.query(TrainingProgram).filter(
        TrainingProgram.gym_id == current_user.gym_id
    ).all()
    return programs

@app.post("/api/chat")
async def send_message(
    message: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat_message = ChatMessage(
        id=str(uuid.uuid4()),
        sender_id=current_user.id,
        sender_name=current_user.name,
        message=message.message,
        type=message.type,
        gym_id=current_user.gym_id
    )
    db.add(chat_message)
    db.commit()
    db.refresh(chat_message)
    return chat_message

@app.get("/api/chat")
async def get_chat_messages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    messages = db.query(ChatMessage).filter(
        ChatMessage.gym_id == current_user.gym_id
    ).order_by(ChatMessage.timestamp).all()
    return messages

@app.post("/api/entries")
async def log_entry(
    entry: GymEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    gym_entry = GymEntry(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        entry_time=entry.entry_time,
        gym_id=current_user.gym_id
    )
    db.add(gym_entry)
    db.commit()
    db.refresh(gym_entry)
    return gym_entry

@app.get("/api/occupancy")
async def get_gym_occupancy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Count users currently in gym (entries without exit)
    current_occupancy = db.query(GymEntry).filter(
        GymEntry.gym_id == current_user.gym_id,
        GymEntry.exit_time.is_(None)
    ).count()
    
    gym = db.query(Gym).filter(Gym.id == current_user.gym_id).first()
    capacity = gym.capacity if gym else 100
    
    occupancy_percentage = (current_occupancy / capacity) * 100
    
    status = "green"
    if occupancy_percentage > 70:
        status = "red"
    elif occupancy_percentage > 30:
        status = "yellow"
    
    return {
        "current": current_occupancy,
        "capacity": capacity,
        "percentage": occupancy_percentage,
        "status": status
    }

# Admin routes
@app.get("/api/admin/pending-users")
async def get_pending_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    pending_users = db.query(User).filter(
        User.gym_id == current_user.gym_id,
        User.status == UserStatus.pending
    ).all()
    return pending_users

@app.post("/api/admin/approve-user/{user_id}")
async def approve_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user = db.query(User).filter(
        User.id == user_id,
        User.gym_id == current_user.gym_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = UserStatus.approved
    db.commit()
    
    return {"message": "User approved"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)