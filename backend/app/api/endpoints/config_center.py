from fastapi import APIRouter, Request
from app.core.response import success
from app.schemas.config_center import (
    AIModelItem,
    ChannelConfig,
    GenerationBehaviorConfigItem,
    PromptConfigItem,
    RoleConfigItem,
    TestModelRequest,
)
from app.services import config_center_service

router = APIRouter()


@router.get('/config-center/prompts/defaults')
async def get_default_prompts(request: Request):
    return success(await config_center_service.get_default_prompts(), request.state.tid)


@router.get('/config-center/ai-models/list')
async def get_ai_model_configs(request: Request):
    return success(await config_center_service.get_ai_model_configs_section(), request.state.tid)


@router.post('/config-center/ai-models/create')
async def create_ai_model_config(request: Request, payload_body: AIModelItem):
    data = await config_center_service.create_ai_model_config_item(payload_body.model_dump(exclude_none=True, exclude_unset=True))
    return success(data, request.state.tid)


@router.put('/config-center/ai-models/edit')
async def edit_ai_model_config(request: Request, payload_body: AIModelItem):
    data = await config_center_service.update_ai_model_config_item(
        str(payload_body.id or '').strip(),
        payload_body.model_dump(exclude_none=True, exclude_unset=True),
    )
    return success(data, request.state.tid)


@router.delete('/config-center/ai-models/delete/{config_id}')
async def delete_ai_model_config(request: Request, config_id: str):
    data = await config_center_service.delete_ai_model_config_item(config_id)
    return success(data, request.state.tid)


@router.get('/config-center/role-configs/list')
async def get_role_configs(request: Request):
    return success(await config_center_service.get_role_configs_section(), request.state.tid)


@router.post('/config-center/role-configs/create')
async def create_role_config(request: Request, payload_body: RoleConfigItem):
    data = await config_center_service.create_role_config_item(payload_body.model_dump(exclude_none=True, exclude_unset=True))
    return success(data, request.state.tid)


@router.put('/config-center/role-configs/edit')
async def update_role_config(request: Request, payload_body: RoleConfigItem):
    normalized_config_id = str(payload_body.id or '').strip()
    data = await config_center_service.update_role_config_item(
        normalized_config_id,
        payload_body.model_dump(exclude_none=True, exclude_unset=True),
    )
    return success(data, request.state.tid)


@router.delete('/config-center/role-configs/delete/{config_id}')
async def delete_role_config(request: Request, config_id: str):
    data = await config_center_service.delete_role_config_item(config_id)
    return success(data, request.state.tid)


@router.get('/config-center/prompts/list')
async def get_prompt_configs(request: Request):
    return success(await config_center_service.get_prompt_configs_section(), request.state.tid)


@router.post('/config-center/prompts/create')
async def create_prompt_config(request: Request, payload_body: PromptConfigItem):
    data = await config_center_service.create_prompt_config_item(payload_body.model_dump(exclude_none=True, exclude_unset=True))
    return success(data, request.state.tid)


@router.put('/config-center/prompts/edit')
async def edit_prompt_config(request: Request, payload_body: PromptConfigItem):
    data = await config_center_service.update_prompt_config_item(
        str(payload_body.id or '').strip(),
        payload_body.model_dump(exclude_none=True, exclude_unset=True),
    )
    return success(data, request.state.tid)


@router.delete('/config-center/prompts/delete/{config_id}')
async def delete_prompt_config(request: Request, config_id: str):
    data = await config_center_service.delete_prompt_config_item(config_id)
    return success(data, request.state.tid)


@router.get('/config-center/behavior/list')
async def get_generation_behavior_configs(request: Request):
    return success(await config_center_service.get_generation_behavior_configs_section(), request.state.tid)


@router.post('/config-center/behavior/create')
async def create_generation_behavior_config(request: Request, payload_body: GenerationBehaviorConfigItem):
    data = await config_center_service.create_generation_behavior_config_item(payload_body.model_dump(exclude_none=True, exclude_unset=True))
    return success(data, request.state.tid)


@router.put('/config-center/behavior/edit')
async def edit_generation_behavior_config(request: Request, payload_body: GenerationBehaviorConfigItem):
    data = await config_center_service.update_generation_behavior_config_item(
        str(payload_body.id or '').strip(),
        payload_body.model_dump(exclude_none=True, exclude_unset=True),
    )
    return success(data, request.state.tid)


@router.delete('/config-center/behavior/delete/{config_id}')
async def delete_generation_behavior_config(request: Request, config_id: str):
    data = await config_center_service.delete_generation_behavior_config_item(config_id)
    return success(data, request.state.tid)


@router.get('/config-center/notifications/list')
async def get_notifications(request: Request):
    return success(await config_center_service.get_notifications_section(), request.state.tid)


@router.post('/config-center/notifications/create/{channel}')
async def create_notification_channel(request: Request, channel: str, payload_body: ChannelConfig):
    data = await config_center_service.create_notification_channel_config(
        channel,
        payload_body.model_dump(exclude_none=True, exclude_unset=True),
    )
    return success(data, request.state.tid)


@router.put('/config-center/notifications/edit/{channel}')
async def edit_notification_channel(request: Request, channel: str, payload_body: ChannelConfig):
    data = await config_center_service.update_notification_channel_config(
        channel,
        payload_body.model_dump(exclude_none=True, exclude_unset=True),
    )
    return success(data, request.state.tid)


@router.delete('/config-center/notifications/delete/{channel}')
async def delete_notification_channel(request: Request, channel: str):
    data = await config_center_service.delete_notification_channel_config(channel)
    return success(data, request.state.tid)


@router.post('/config-center/models/test')
async def test_model_connection(request: Request, payload: TestModelRequest):
    return success(await config_center_service.test_model_connection(payload), request.state.tid)
