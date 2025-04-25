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
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, onupdate=func.now())

    profiles = relationship("Profile", back_populates="user")

class Profile(Base):
    __tablename__ = 'profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    profile_name = Column(String(40), nullable=False)
    type_of_epilepsy = Column(String(20))
    age = Column(Integer)
    sex = Column(String(20))
    timezone = Column(String(3))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, onupdate=func.now())

    user = relationship("User", back_populates="profiles")
    drugs = relationship("Drug", secondary="profile_drugs", back_populates="profiles")

    def to_dict(self):
        return {
            "id": self.id,
            "profile_name": self.profile_name,
            "type_of_epilepsy": self.type_of_epilepsy,
            "age": self.age,
            "sex": self.sex,
            "timezone": self.timezone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Drug(Base):
    __tablename__ = 'drugs'

    id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False)

    profiles = relationship("Profile", secondary="profile_drugs", back_populates="drugs")

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
    #creator_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    #type_of_seizure = Column(String(30), nullable=True)
    #postical_duration = Column(Integer(), nullable=True)
    #postical_symptoms = Column(String(250), nullable=True)
    triggers = Column(String, nullable=True)
    location = Column(String(30), nullable=True)
    symptoms = Column(String, nullable=True)

class TrustedPersonProfiles(Base):
    __tablename__ = "trusted_person_profiles"

    id = Column(Integer, primary_key=True)
    trusted_person_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    profile_owner_id = Column(Integer, ForeignKey("users.id"))
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"))
    can_read = Column(Boolean, nullable=False, default=True)
    can_edit = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class TrustedPersonRequest(Base):
    __tablename__ = "trusted_person_requests"

    id = Column(String, primary_key=True, server_default=func.now())
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recepient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transmitted_profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), server_default=text("NOW() + INTERVAL '10 minutes'"), nullable=False)

'''
class MedicationCourse(Base):
    __tablename__ = 'medication_courses'

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)

    # Если препарат выбран из справочника
    drug_id = Column(Integer, ForeignKey('drugs.id'), nullable=True)

    # Если препарат введен вручную
    manual_entry_name = Column(String(100), nullable=True)  # Например: "Кеппра 500мг"
    is_manual = Column(Boolean, default=False)  # True — пользователь ввел руками

    dosage = Column(String(50))       # Например: "100мг 2 раза в день"
    form = Column(String(30))         # Таблетки, сироп и т.д.
    frequency = Column(String(30))    # Например: "2 раза в день"
    time_slots = Column(ARRAY(String), nullable=True)  # Временные точки приема
    reminder_enabled = Column(Boolean, default=False)

    raw_input = Column(String(200), nullable=True)  # Сырой текст от пользователя
    notes = Column(String(200), nullable=True)      # Примечания

    start_date = Column(Date)
    end_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    drug = relationship("Drug", back_populates="medication_courses")
    profile = relationship("Profile", back_populates="medication_courses")'''

profile_drugs = Table(
    'profile_drugs',
    Base.metadata,
    Column('profile_id', Integer, ForeignKey('profiles.id', ondelete="CASCADE"), primary_key=True),
    Column('drug_id', Integer, ForeignKey('drugs.id', ondelete="CASCADE"), primary_key=True)
)
