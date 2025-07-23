import enum
import uuid
from sqlalchemy import ( Column, Integer, BigInteger, Index,
                        String, Enum, ForeignKey, Table,
                        DateTime, Boolean, Time, UniqueConstraint, PrimaryKeyConstraint,
                        Date
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.sql import text

from database.db_init import Base

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
    timezone = Column(String(3))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    keyword_hash = Column(String(60))
    current_profile = Column(Integer, default=None, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, onupdate=func.now())

    profiles = relationship("Profile", back_populates="user")

    def to_dict(self):
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'telegram_username': self.telegram_username,
            'telegram_fullname': self.telegram_fullname,
            'name': self.name,
            'login': self.login,
            'timezone': self.timezone,
            'created_at': self.created_at,
            'current_profile': self.current_profile,
            'updated_at': self.updated_at
        }

class Profile(Base):
    __tablename__ = 'profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    profile_name = Column(String(40), nullable=False)
    type_of_epilepsy = Column(String(100))
    age = Column(Integer)
    sex = Column(String(20))
    biological_species = Column(String(30))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, onupdate=func.now())

    user = relationship("User", back_populates="profiles")

    def to_dict(self):
        return {
            "id": self.id,
            "profile_name": self.profile_name,
            "type_of_epilepsy": self.type_of_epilepsy,
            "age": self.age,
            "sex": self.sex,
            "biological_species": self.biological_species,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Seizure(Base):
    __tablename__ = 'seizures'

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('profiles.id', ondelete="CASCADE"), nullable=False)
    date = Column(String(25))
    time = Column(String(25), nullable=True)
    severity = Column(String(50), nullable=True)
    duration = Column(Integer, nullable=True)
    comment = Column(String(150), nullable=True)
    count = Column(Integer, nullable=True)

    video_tg_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    creator_login = Column(String(25), nullable=False)
    type_of_seizure = Column(String(50), nullable=True)
    triggers = Column(String, nullable=True)
    location = Column(String(30), nullable=True)
    symptoms = Column(String, nullable=True)

class SeizureSymptom(Base):
    __tablename__ = 'seizure_symptoms'
    seizure_id = Column(Integer, ForeignKey("seizures.id", ondelete="CASCADE"))
    symptom_id = Column(Integer, ForeignKey("symptoms.id", ondelete="CASCADE"))
    __table_args__ = (
        PrimaryKeyConstraint('seizure_id', 'symptom_id'),
    )
class SeizureTrigger(Base):
    __tablename__ = 'seizure_triggers'
    seizure_id = Column(Integer, ForeignKey("seizures.id", ondelete="CASCADE"))
    trigger_id = Column(Integer, ForeignKey("triggers.id", ondelete="CASCADE"))
    __table_args__ = (
        PrimaryKeyConstraint('seizure_id', 'trigger_id'),
    )
class Symptom(Base):
    __tablename__ = 'symptoms'
    id = Column(Integer, primary_key=True)
    symptom_name = Column(String(100), nullable=False)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True)
    __table_args__ = (UniqueConstraint('symptom_name', 'profile_id', name='uix_symptom_name_profile'),)
class Trigger(Base):
    __tablename__ = 'triggers'
    id = Column(Integer, primary_key=True)
    trigger_name = Column(String(100), nullable=False)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True)
    __table_args__ = (UniqueConstraint('trigger_name', 'profile_id', name='uix_trigger_name_profile'),)


class TrustedPersonProfiles(Base):
    __tablename__ = "trusted_person_profiles"

    id = Column(Integer, primary_key=True)
    trusted_person_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    profile_owner_id = Column(Integer, ForeignKey("users.id"))
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"))
    can_edit = Column(Boolean, nullable=False, default=True)
    get_notification = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    def to_dict(self):
        return {
            'id': self.id,
            'trusted_person_user_id': self.trusted_person_user_id,
            'profile_owner_id': self.profile_owner_id,
            'profile_id': self.profile_id,
            #'can_read': self.can_read,
            'can_edit': self.can_edit,
            'get_notification': self.get_notification,
            'created_at': self.created_at
        }

class TrustedPersonRequest(Base):
    __tablename__ = "trusted_person_requests"

    id = Column(String, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recepient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transmitted_profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), server_default=text("NOW() + INTERVAL '10 minutes'"), nullable=False)

class UserNotifications(Base):
    __tablename__ = 'user_notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    notify_time = Column(Time, nullable=False)
    note = Column(String(100), nullable=False)
    pattern = Column(String(20), nullable=False, default="daily")
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint('user_id', 'notify_time', name='uix_user_notify_time'),
    )

class MedicationCourse(Base):
    __tablename__ = 'medication_courses'

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)

    medication_name = Column(String(100))
    dosage = Column(String(50))
    frequency = Column(String(30))
    notes = Column(String(200))

    start_date = Column(Date)
    end_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
