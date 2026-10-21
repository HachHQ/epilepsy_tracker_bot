import enum
from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql import func, text

from database.db_init import Base
from database.seizure_values import parse_seizure_date, parse_seizure_time


class RequestStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    telegram_fullname: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str | None] = mapped_column(String(25))
    login: Mapped[str] = mapped_column(String(25), nullable=False, unique=True)
    timezone: Mapped[str | None] = mapped_column(String(3))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    keyword_hash: Mapped[str | None] = mapped_column(String(60))
    current_profile: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profiles: Mapped[list["Profile"]] = relationship(back_populates="user")

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    profile_name: Mapped[str] = mapped_column(String(40), nullable=False)
    type_of_epilepsy: Mapped[str | None] = mapped_column(String(100))
    age: Mapped[int | None] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(String(20))
    biological_species: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seizures_retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="profiles")
    seizures: Mapped[list["Seizure"]] = relationship(back_populates="profile")
    symptoms: Mapped[list["Symptom"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    triggers: Mapped[list["Trigger"]] = relationship(back_populates="profile", cascade="all, delete-orphan")

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(Integer, ForeignKey('profiles.id', ondelete="RESTRICT"), nullable=False)
    date: Mapped[date | None] = mapped_column(Date)
    time: Mapped[time | None] = mapped_column(Time, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment: Mapped[str | None] = mapped_column(String(150), nullable=True)
    count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    video_tg_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    creator_login: Mapped[str] = mapped_column(String(25), nullable=False)
    type_of_seizure: Mapped[str | None] = mapped_column(String(50), nullable=True)
    triggers: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String(30), nullable=True)
    symptoms: Mapped[str | None] = mapped_column(String, nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @validates("date")
    def _coerce_date(self, _key: str, value):
        return parse_seizure_date(value)

    @validates("time")
    def _coerce_time(self, _key: str, value):
        return parse_seizure_time(value)

    profile: Mapped["Profile"] = relationship(back_populates="seizures")
    symptom_links: Mapped[list["SeizureSymptom"]] = relationship(
        back_populates="seizure", cascade="all, delete-orphan"
    )
    trigger_links: Mapped[list["SeizureTrigger"]] = relationship(
        back_populates="seizure", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_seizures_profile_id_date", "profile_id", "date"),
    )

class SeizureSymptom(Base):
    __tablename__ = 'seizure_symptoms'
    seizure_id: Mapped[int] = mapped_column(Integer, ForeignKey("seizures.id", ondelete="CASCADE"), primary_key=True)
    symptom_id: Mapped[int] = mapped_column(Integer, ForeignKey("symptoms.id", ondelete="CASCADE"), primary_key=True)
    seizure: Mapped["Seizure"] = relationship(back_populates="symptom_links")
    symptom: Mapped["Symptom"] = relationship(back_populates="seizure_links")

class SeizureTrigger(Base):
    __tablename__ = 'seizure_triggers'
    seizure_id: Mapped[int] = mapped_column(Integer, ForeignKey("seizures.id", ondelete="CASCADE"), primary_key=True)
    trigger_id: Mapped[int] = mapped_column(Integer, ForeignKey("triggers.id", ondelete="CASCADE"), primary_key=True)
    seizure: Mapped["Seizure"] = relationship(back_populates="trigger_links")
    trigger: Mapped["Trigger"] = relationship(back_populates="seizure_links")

class Symptom(Base):
    __tablename__ = 'symptoms'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symptom_name: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True)
    profile: Mapped["Profile | None"] = relationship(back_populates="symptoms")
    seizure_links: Mapped[list["SeizureSymptom"]] = relationship(
        back_populates="symptom", cascade="all, delete-orphan"
    )
    __table_args__ = (UniqueConstraint('symptom_name', 'profile_id', name='uix_symptom_name_profile'),)

class Trigger(Base):
    __tablename__ = 'triggers'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger_name: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True)
    profile: Mapped["Profile | None"] = relationship(back_populates="triggers")
    seizure_links: Mapped[list["SeizureTrigger"]] = relationship(
        back_populates="trigger", cascade="all, delete-orphan"
    )
    __table_args__ = (UniqueConstraint('trigger_name', 'profile_id', name='uix_trigger_name_profile'),)


class TrustedPersonProfiles(Base):
    __tablename__ = "trusted_person_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trusted_person_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    profile_owner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    profile_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"))
    can_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    can_edit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    get_notification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'trusted_person_user_id': self.trusted_person_user_id,
            'profile_owner_id': self.profile_owner_id,
            'profile_id': self.profile_id,
            'can_read': self.can_read,
            'can_edit': self.can_edit,
            'get_notification': self.get_notification,
            'created_at': self.created_at
        }

    __table_args__ = (
        Index("ix_trusted_person_profiles_trusted_user", "trusted_person_user_id"),
        Index("ix_trusted_person_profiles_owner_profile", "profile_owner_id", "profile_id"),
        UniqueConstraint(
            "trusted_person_user_id",
            "profile_id",
            name="uq_trusted_person_profile",
        ),
    )

class TrustedPersonRequest(Base):
    __tablename__ = "trusted_person_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    recepient_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    transmitted_profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW() + INTERVAL '24 hours'"), nullable=False
    )

class UserNotifications(Base):
    __tablename__ = 'user_notifications'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    notify_time: Mapped[time] = mapped_column(Time, nullable=False)
    note: Mapped[str] = mapped_column(String(100), nullable=False)
    pattern: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")
    is_enabled: Mapped[bool | None] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint('user_id', 'notify_time', name='uix_user_notify_time'),
    )

class MedicationCourse(Base):
    __tablename__ = 'medication_courses'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)

    medication_name: Mapped[str | None] = mapped_column(String(100))
    dosage: Mapped[str | None] = mapped_column(String(50))
    frequency: Mapped[str | None] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(String(200))

    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
