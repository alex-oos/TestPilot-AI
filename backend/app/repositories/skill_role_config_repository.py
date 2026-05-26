"""Skill 角色绑定仓储。

作者：Zhao Wang
"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_role_config_model import SkillRoleConfig


class SkillRoleConfigRepository:
    """Skill 角色绑定 CRUD。"""

    @staticmethod
    async def list(db: AsyncSession) -> list[SkillRoleConfig]:
        """列出全部角色绑定。"""
        result = await db.execute(select(SkillRoleConfig).order_by(SkillRoleConfig.id.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def clear(db: AsyncSession) -> int:
        """清空全部绑定。"""
        result = await db.execute(delete(SkillRoleConfig))
        return int(result.rowcount or 0)

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> SkillRoleConfig:
        """创建绑定记录。"""
        row = SkillRoleConfig(**kwargs)
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def get_by_config_id(db: AsyncSession, config_id: str) -> SkillRoleConfig | None:
        """按 config_id 查询。"""
        result = await db.execute(
            select(SkillRoleConfig).where(SkillRoleConfig.config_id == config_id)
        )
        return result.scalars().first()

    @staticmethod
    async def delete_by_config_id(db: AsyncSession, config_id: str) -> int:
        """按 config_id 删除。"""
        result = await db.execute(
            delete(SkillRoleConfig).where(SkillRoleConfig.config_id == config_id)
        )
        return int(result.rowcount or 0)
