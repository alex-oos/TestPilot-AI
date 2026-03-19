from fastapi import APIRouter, Request
from app.core.response import success
from app.schemas.config_center import ConfigCenterUpdateRequest, TestModelRequest
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


@router.post('/settings/config-center/models/test')
@router.post('/config-center/test-model')
async def test_model_connection(request: Request, payload: TestModelRequest):
    return success(await config_center_service.test_model_connection(payload), request.state.tid)
