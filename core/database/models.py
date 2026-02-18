from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Float, JSON, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Case(Base, TimestampMixin):
    __tablename__ = "cases"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100))  # SEO, Development, etc.
    description: Mapped[str] = mapped_column(Text)
    results: Mapped[str] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    project_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Service(Base, TimestampMixin):
    __tablename__ = "services"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    price_range: Mapped[str] = mapped_column(String(100))
    process: Mapped[str] = mapped_column(Text)
    timeline: Mapped[str] = mapped_column(String(100))

class Lead(Base, TimestampMixin):
    __tablename__ = "leads"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True)
    username: Mapped[Optional[str]] = mapped_column(String(100))
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_interaction: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    lead_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Adaptive Learning Fields
    style_profile: Mapped[Optional[str]] = mapped_column(Text)  # Analyzed style of the user
    context_memory: Mapped[Optional[str]] = mapped_column(Text) # Key facts learned about the user
    
    # Follow-up Tracking
    follow_up_level: Mapped[int] = mapped_column(Integer, default=0) # 0: none, 1: 1 day, 2: 3 days, 3: 5 days
    follow_up_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_outreach_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    messages: Mapped[List["MessageLog"]] = relationship(back_populates="lead")
    
    # Handover Status
    is_human_managed: Mapped[bool] = mapped_column(Boolean, default=False)
    handover_reason: Mapped[Optional[str]] = mapped_column(String(255))

    # New Fields for TODO tasks
    tier: Mapped[Optional[str]] = mapped_column(String(20), default="COLD")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    meeting_scheduled: Mapped[bool] = mapped_column(Boolean, default=False)

class MessageLog(Base, TimestampMixin):
    __tablename__ = "message_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    direction: Mapped[str] = mapped_column(String(20))  # incoming, outgoing
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[Optional[str]] = mapped_column(String(100))
    category: Mapped[Optional[str]] = mapped_column(String(100))
    lead_score: Mapped[Optional[float]] = mapped_column(Float)
    ai_response: Mapped[Optional[str]] = mapped_column(Text)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="sent") # sent, failed, read
    telegram_msg_id: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    lead: Mapped["Lead"] = relationship(back_populates="messages")

class FAQ(Base, TimestampMixin):
    __tablename__ = "faqs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(100))
