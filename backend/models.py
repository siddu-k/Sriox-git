from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    websites = relationship("Website", back_populates="owner", cascade="all, delete-orphan")
    redirects = relationship("Redirect", back_populates="owner", cascade="all, delete-orphan")
    github_mappings = relationship("GitHubMapping", back_populates="owner", cascade="all, delete-orphan")

class Website(Base):
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    subdomain = Column(String, unique=True, index=True)
    folder_path = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="websites")

class Redirect(Base):
    __tablename__ = "redirects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    target_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="redirects")

class GitHubMapping(Base):
    __tablename__ = "github_mappings"

    id = Column(Integer, primary_key=True, index=True)
    subdomain = Column(String, unique=True, index=True)
    github_username = Column(String)
    repository_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="github_mappings")