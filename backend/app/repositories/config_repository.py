from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppConfig


class ConfigRepository:
    @staticmethod
    def get_by_key(db: Session, config_key: str) -> Optional[AppConfig]:
        return db.scalar(select(AppConfig).where(AppConfig.config_key == config_key))

    @staticmethod
    def create(
        db: Session,
        *,
        config_key: str,
        config_json: str,
        created_at: str,
        updated_at: str,
    ) -> AppConfig:
        row = AppConfig(
            config_key=config_key,
            config_json=config_json,
            created_at=created_at,
            updated_at=updated_at,
        )
        db.add(row)
        return row
