from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    house_number = Column(String, nullable=True)
    entrance = Column(String, nullable=True)
    floor = Column(String, nullable=True)
    room_number = Column(String, nullable=True)
    is_subscribed = Column(Boolean, default=False)
    subscription_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_type = Column(String)          # order_now / order_later
    pickup_time = Column(String, nullable=True)
    house_number = Column(String)
    entrance = Column(String)
    floor = Column(String)
    room_number = Column(String)
    door_or_concierge = Column(String)
    status = Column(String, default="new")  # new / in_progress / done / cancelled
    price = Column(Integer, default=150)
    is_paid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User")