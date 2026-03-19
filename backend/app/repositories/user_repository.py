from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        return db.scalar(select(User).where(User.username == username))

    @staticmethod
    def create(db: Session, *, username: str, password: str, created_at: str, updated_at: str) -> User:
        user = User(
            username=username,
            password=password,
            is_active=True,
            created_at=created_at,
            updated_at=updated_at,
        )
        db.add(user)
        db.flush()
        return user
