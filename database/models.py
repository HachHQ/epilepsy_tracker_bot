from sqlalchemy import Column, Integer, BigInteger, String, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship
from database.db_init import Base
from datetime import datetime

class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    telegram_username = Column(String)
    telegram_fullname = Column(String)
    name = Column(String)
    login = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    profiles = relationship("Profile", back_populates="user")

class Profile(Base):
    __tablename__ = 'profiles'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    profile_name = Column(String, nullable=False)
    type_of_epilepsy = Column(String)
    age = Column(Integer)
    sex = Column(String)
    timezone = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="profiles")
    drugs = relationship("Drug", secondary="profile_drugs", back_populates="profiles")

class Drug(Base):
    __tablename__ = 'drugs'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    profiles = relationship("Profile", secondary="profile_drugs", back_populates="drugs")

profile_drugs = Table(
    'profile_drugs',
    Base.metadata,
    Column('profile_id', Integer, ForeignKey('profiles.id'), primary_key=True),
    Column('drug_id', Integer, ForeignKey('drugs.id'), primary_key=True)
)
