from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AIConfig, GenerationBehaviorConfig, NotificationConfig, PromptConfig, RoleConfig


class ConfigRepository:
    @staticmethod
    def list_ai_configs(db: Session) -> list[AIConfig]:
        return list(db.scalars(select(AIConfig).order_by(AIConfig.id.asc())).all())

    @staticmethod
    def clear_ai_configs(db: Session) -> int:
        result = db.execute(delete(AIConfig))
        return int(result.rowcount or 0)

    @staticmethod
    def create_ai_config(db: Session, **kwargs) -> AIConfig:
        row = AIConfig(**kwargs)
        db.add(row)
        return row

    @staticmethod
    def list_role_configs(db: Session) -> list[RoleConfig]:
        return list(db.scalars(select(RoleConfig).order_by(RoleConfig.id.asc())).all())

    @staticmethod
    def clear_role_configs(db: Session) -> int:
        result = db.execute(delete(RoleConfig))
        return int(result.rowcount or 0)

    @staticmethod
    def create_role_config(db: Session, **kwargs) -> RoleConfig:
        row = RoleConfig(**kwargs)
        db.add(row)
        return row

    @staticmethod
    def list_prompt_configs(db: Session) -> list[PromptConfig]:
        return list(db.scalars(select(PromptConfig).order_by(PromptConfig.id.asc())).all())

    @staticmethod
    def clear_prompt_configs(db: Session) -> int:
        result = db.execute(delete(PromptConfig))
        return int(result.rowcount or 0)

    @staticmethod
    def create_prompt_config(db: Session, **kwargs) -> PromptConfig:
        row = PromptConfig(**kwargs)
        db.add(row)
        return row

    @staticmethod
    def list_notification_configs(db: Session) -> list[NotificationConfig]:
        return list(db.scalars(select(NotificationConfig).order_by(NotificationConfig.id.asc())).all())

    @staticmethod
    def clear_notification_configs(db: Session) -> int:
        result = db.execute(delete(NotificationConfig))
        return int(result.rowcount or 0)

    @staticmethod
    def create_notification_config(db: Session, **kwargs) -> NotificationConfig:
        row = NotificationConfig(**kwargs)
        db.add(row)
        return row

    @staticmethod
    def list_generation_behavior_configs(db: Session) -> list[GenerationBehaviorConfig]:
        return list(db.scalars(select(GenerationBehaviorConfig).order_by(GenerationBehaviorConfig.id.asc())).all())

    @staticmethod
    def clear_generation_behavior_configs(db: Session) -> int:
        result = db.execute(delete(GenerationBehaviorConfig))
        return int(result.rowcount or 0)

    @staticmethod
    def create_generation_behavior_config(db: Session, **kwargs) -> GenerationBehaviorConfig:
        row = GenerationBehaviorConfig(**kwargs)
        db.add(row)
        return row
