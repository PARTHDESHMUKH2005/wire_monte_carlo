import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, JSON
from database.connection import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    subscription_tier = Column(String(50), default="free")
    briefs_enabled = Column(Boolean, default=False)
    whatsapp_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    portfolio_json = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    intent = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class RiskRun(Base):
    __tablename__ = "risk_runs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quant_metrics_json = Column(Text, nullable=True)
    forecast_json = Column(Text, nullable=True)
    report_markdown = Column(Text, nullable=True)
    health_score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    metric = Column(String(100), nullable=False)
    threshold = Column(Float, nullable=False)
    active = Column(Boolean, default=True)
    last_triggered = Column(DateTime, nullable=True)


class UserPreference(Base):
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    horizon = Column(String(50), nullable=True)
    risk_tolerance = Column(String(50), nullable=True)
    tax_sensitivity = Column(String(50), nullable=True)
    concerns_json = Column(Text, nullable=True)
    goals_json = Column(Text, nullable=True)


class BriefLog(Base):
    __tablename__ = "brief_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    channel = Column(String(50), nullable=False)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
