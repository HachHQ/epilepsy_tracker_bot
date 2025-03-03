from sqlalchemy import Column, Integer, BigInteger, Index, TIMESTAMP, String, Enum, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.db_init import Base
from datetime import datetime, timedelta
import enum
import uuid

class RequestStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"

class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    telegram_username = Column(String(64))
    telegram_fullname = Column(String(64))
    name = Column(String(25))
    login = Column(String(25), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    profiles = relationship("Profile", back_populates="user")

class Profile(Base):
    __tablename__ = 'profiles'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    profile_name = Column(String(40), nullable=False)
    type_of_epilepsy = Column(String(20))
    age = Column(Integer)
    sex = Column(String(20))
    timezone = Column(String(3))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="profiles")
    drugs = relationship("Drug", secondary="profile_drugs", back_populates="profiles")

class Drug(Base):
    __tablename__ = 'drugs'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False)

    profiles = relationship("Profile", secondary="profile_drugs", back_populates="drugs")

class Seizure(Base):
    __tablename__ = 'seizures'

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('profiles.id'), nullable=False)
    date = Column(String(25))
    time = Column(String(25))
    severity = Column(String(50), nullable=True)
    duration = Column(Integer)
    comment = Column(String(150))
    count = Column(Integer, nullable=True)

    video_tg_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    triggers = Column(String, nullable=True)
    location = Column(String(30), nullable=True)
    symptoms = Column(String, nullable=True)

class TrustedPersonRequest(Base):
    __tablename__ = "trusted_person_requests"

    request_uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, nullable=False)
    recipient_id = Column(BigInteger, nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow(), nullable=False)
    expires_at = Column(DateTime, default=datetime.utcnow() + timedelta(), nullable=False)

    __table_args__ = (
        Index("idx_recipient", "recipient_id"),
    )

profile_drugs = Table(
    'profile_drugs',
    Base.metadata,
    Column('profile_id', Integer, ForeignKey('profiles.id'), primary_key=True),
    Column('drug_id', Integer, ForeignKey('drugs.id'), primary_key=True)
)
