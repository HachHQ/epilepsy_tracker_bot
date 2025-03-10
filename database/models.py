import enum
import uuid
from sqlalchemy import ( Column, Integer, BigInteger, Index,
                        String, Enum, ForeignKey, Table,
                        DateTime, Boolean)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql import text

from database.db_init import Base
from datetime import datetime, timedelta, timezone

class RequestStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    telegram_username = Column(String(64))
    telegram_fullname = Column(String(64))
    name = Column(String(25))
    login = Column(String(25), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    current_profile = Column(Integer, default=None, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    profiles = relationship("Profile", back_populates="user")

class Profile(Base):
    __tablename__ = 'profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    profile_name = Column(String(40), nullable=False)
    type_of_epilepsy = Column(String(20))
    age = Column(Integer)
    sex = Column(String(20))
    timezone = Column(String(3))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="profiles")
    drugs = relationship("Drug", secondary="profile_drugs", back_populates="profiles")

class Drug(Base):
    __tablename__ = 'drugs'

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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    triggers = Column(String, nullable=True)
    location = Column(String(30), nullable=True)
    symptoms = Column(String, nullable=True)

class TrustedPersonProfiles(Base):
    __tablename__ = "trusted_person_profiles"

    id = Column(Integer, primary_key=True)
    trusted_person_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    profile_owner_id = Column(Integer, ForeignKey("users.id"))
    profile_id = Column(Integer, ForeignKey("profiles.id"))
    can_read = Column(Boolean, nullable=False, default=True)
    can_edit = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class TrustedPersonRequest(Base):
    __tablename__ = "trusted_person_requests"

    id = Column(String, primary_key=True, server_default=func.now())
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recepient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transmitted_profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), server_default=text("NOW() + INTERVAL '10 minutes'"), nullable=False)

profile_drugs = Table(
    'profile_drugs',
    Base.metadata,
    Column('profile_id', Integer, ForeignKey('profiles.id', ondelete="CASCADE"), primary_key=True),
    Column('drug_id', Integer, ForeignKey('drugs.id', ondelete="CASCADE"), primary_key=True)
)
