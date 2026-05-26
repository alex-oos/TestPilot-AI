"""QA Skill 角色绑定配置 API（与 Skill 库管理分离）。

作者：Zhao Wang
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.ai.skills.role_skill_config import apply_role_config_update, build_role_config_view
from app.core.auth import get_current_user
from app.core.response import success

router = APIRouter()


class SkillRoleBindingItem(BaseModel):
    """单角色 Skill 绑定项。"""

    id: str | None = None
    role: str
    skill_id: str
    enabled: bool = True


class SkillRoleBindingUpdateRequest(BaseModel):
    """Skill 角色绑定更新请求。"""

    qa_skills_enabled: bool | None = None
    skill_configs: list[SkillRoleBindingItem] | None = None


@router.get("/ai/skill-role-config")
async def get_skill_role_binding(request: Request, current_user: dict = Depends(get_current_user)):
    """读取三角色 Skill 绑定与全局开关。"""
    data = await build_role_config_view()
    return success(data, request.state.tid)


@router.put("/ai/skill-role-config")
async def update_skill_role_binding(
    payload: SkillRoleBindingUpdateRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """更新三角色 Skill 绑定与全局开关。"""
    body: dict = {}
    if payload.qa_skills_enabled is not None:
        body["qa_skills_enabled"] = payload.qa_skills_enabled
    if payload.skill_configs is not None:
        body["skill_configs"] = [
            {
                "id": item.id or f"default-{item.role}-skill",
                "role": item.role,
                "skill_id": item.skill_id,
                "enabled": item.enabled,
            }
            for item in payload.skill_configs
        ]
    data = await apply_role_config_update(body)
    return success(data, request.state.tid)
