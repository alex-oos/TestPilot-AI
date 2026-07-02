"""QA Skill 全局设置仓储。

作者：Zhao Wang
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_settings_model import SkillSettings


class SkillSettingsRepository:
    """Skill 全局设置 CRUD。"""

    @staticmethod
    async def get(db: AsyncSession) -> SkillSettings | None:
        """读取全局设置（id=1）。"""
        result = await db.execute(select(SkillSettings).where(SkillSettings.id == 1))
        return result.scalars().first()

    @staticmethod
    async def upsert(db: AsyncSession, *, qa_skills_enabled: bool, updated_at: str) -> SkillSettings:
        """写入或更新全局设置。"""
        row = await SkillSettingsRepository.get(db)
        if row is None:
            row = SkillSettings(
                id=1,
                qa_skills_enabled=qa_skills_enabled,
                created_at=updated_at,
                updated_at=updated_at,
            )
            db.add(row)
        else:
            row.qa_skills_enabled = qa_skills_enabled
            row.updated_at = updated_at
        await db.flush()
        return row
