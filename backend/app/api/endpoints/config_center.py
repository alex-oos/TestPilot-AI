from fastapi import APIRouter, Request
from app.core.response import success
from app.schemas.config_center import (
    AIModelConfigsUpdateRequest,
    ConfigCenterUpdateRequest,
    GenerationBehaviorConfigsUpdateRequest,
    NotificationsUpdateRequest,
    PromptConfigsUpdateRequest,
    RoleConfigsUpdateRequest,
    TestModelRequest,
)
from app.services import config_center_service

router = APIRouter()


@router.get('/settings/config-center')
@router.get('/config-center')
async def get_config_center(request: Request):
    return success(config_center_service.get_config_center(), request.state.tid)


@router.put('/settings/config-center')
@router.put('/config-center')
async def update_config_center(request: Request, payload_body: ConfigCenterUpdateRequest):
    data = config_center_service.update_config_center(payload_body)
    return success(data, request.state.tid)


@router.get('/settings/config-center/prompts/defaults')
@router.get('/config-center/default-prompts')
async def get_default_prompts(request: Request):
    return success(config_center_service.get_default_prompts(), request.state.tid)


@router.get('/settings/config-center/ai-models')
@router.get('/config-center/ai-models')
async def get_ai_model_configs(request: Request):
    return success(config_center_service.get_ai_model_configs_section(), request.state.tid)


@router.put('/settings/config-center/ai-models')
@router.put('/config-center/ai-models')
async def update_ai_model_configs(request: Request, payload_body: AIModelConfigsUpdateRequest):
    data = config_center_service.update_ai_model_configs_section(payload_body.model_dump())
    return success(data, request.state.tid)


@router.get('/settings/config-center/role-configs')
@router.get('/config-center/role-configs')
@router.get('/settings/config-center/role-models')
@router.get('/config-center/role-models')
async def get_role_configs(request: Request):
    return success(config_center_service.get_role_configs_section(), request.state.tid)


@router.put('/settings/config-center/role-configs')
@router.put('/config-center/role-configs')
@router.put('/settings/config-center/role-models')
@router.put('/config-center/role-models')
async def update_role_configs(request: Request, payload_body: RoleConfigsUpdateRequest):
    data = config_center_service.update_role_configs_section(payload_body.model_dump(exclude_none=True, exclude_unset=True))
    return success(data, request.state.tid)


@router.get('/settings/config-center/prompts')
@router.get('/config-center/prompts')
async def get_prompt_configs(request: Request):
    return success(config_center_service.get_prompt_configs_section(), request.state.tid)


@router.put('/settings/config-center/prompts')
@router.put('/config-center/prompts')
async def update_prompt_configs(request: Request, payload_body: PromptConfigsUpdateRequest):
    data = config_center_service.update_prompt_configs_section(payload_body.model_dump(exclude_none=True, exclude_unset=True))
    return success(data, request.state.tid)


@router.get('/settings/config-center/behavior')
@router.get('/config-center/behavior')
async def get_generation_behavior_configs(request: Request):
    return success(config_center_service.get_generation_behavior_configs_section(), request.state.tid)


@router.put('/settings/config-center/behavior')
@router.put('/config-center/behavior')
async def update_generation_behavior_configs(request: Request, payload_body: GenerationBehaviorConfigsUpdateRequest):
    data = config_center_service.update_generation_behavior_configs_section(payload_body.model_dump())
    return success(data, request.state.tid)


@router.get('/settings/config-center/notifications')
@router.get('/config-center/notifications')
async def get_notifications(request: Request):
    return success(config_center_service.get_notifications_section(), request.state.tid)


@router.put('/settings/config-center/notifications')
@router.put('/config-center/notifications')
async def update_notifications(request: Request, payload_body: NotificationsUpdateRequest):
    data = config_center_service.update_notifications_section(payload_body.model_dump(exclude_none=True, exclude_unset=True))
    return success(data, request.state.tid)


@router.post('/settings/config-center/models/test')
@router.post('/config-center/test-model')
async def test_model_connection(request: Request, payload: TestModelRequest):
    return success(await config_center_service.test_model_connection(payload), request.state.tid)
