from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data_base.models import Base, User
from typing import Optional

engine = create_engine("sqlite:///ecoflow.db")
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)

def get_or_create_user(session, telegram_id: int, username: Optional[str]):
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user is None:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user