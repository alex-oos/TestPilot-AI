from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success, fail
from app.models.api_automation_model import (
    ApiEndpoint, ApiEnvironment, ApiTestCase, ApiExecution,
)
from app.util.time_utils import now_str

router = APIRouter(prefix="/api-automation", tags=["API Automation"])


# ---- Endpoints ----
@router.get("/endpoints")
async def list_endpoints(project_id: int = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(ApiEndpoint).order_by(ApiEndpoint.id.desc())
    if project_id:
        stmt = stmt.where(ApiEndpoint.project_id == project_id)
    result = await db.execute(stmt)
    return success([{
        "id": e.id, "name": e.name, "method": e.method, "path": e.path,
        "description": e.description, "tags": e.tags,
    } for e in result.scalars().all()])


@router.post("/endpoints")
async def create_endpoint(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    ep = ApiEndpoint(
        project_id=body.get("project_id"), name=body.get("name", ""),
        method=body.get("method", "GET"), path=body.get("path", ""),
        description=body.get("description"), headers_json=body.get("headers_json"),
        body_json=body.get("body_json"), response_json=body.get("response_json"),
        tags=body.get("tags"), created_at=ts, updated_at=ts,
    )
    db.add(ep)
    await db.commit()
    await db.refresh(ep)
    return success({"id": ep.id})


@router.put("/endpoints/{ep_id}")
async def update_endpoint(ep_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    ep = await db.get(ApiEndpoint, ep_id)
    if not ep:
        return fail("接口不存在")
    for field in ("name", "method", "path", "description", "headers_json", "body_json", "response_json", "tags"):
        if field in body:
            setattr(ep, field, body[field])
    ep.updated_at = now_str()
    await db.commit()
    return success({"id": ep.id})


@router.delete("/endpoints/{ep_id}")
async def delete_endpoint(ep_id: int, db: AsyncSession = Depends(get_db)):
    ep = await db.get(ApiEndpoint, ep_id)
    if not ep:
        return fail("接口不存在")
    await db.delete(ep)
    await db.commit()
    return success(None)


# ---- Environments ----
@router.get("/environments")
async def list_environments(project_id: int = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(ApiEnvironment).order_by(ApiEnvironment.id.desc())
    if project_id:
        stmt = stmt.where(ApiEnvironment.project_id == project_id)
    result = await db.execute(stmt)
    return success([{
        "id": e.id, "name": e.name, "base_url": e.base_url,
        "variables_json": e.variables_json, "is_default": e.is_default,
    } for e in result.scalars().all()])


@router.post("/environments")
async def create_environment(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    env = ApiEnvironment(
        project_id=body.get("project_id"), name=body.get("name", ""),
        base_url=body.get("base_url", ""), variables_json=body.get("variables_json"),
        is_default=body.get("is_default", "false"), created_at=ts, updated_at=ts,
    )
    db.add(env)
    await db.commit()
    return success({"id": env.id})


# ---- Test Cases ----
@router.get("/test-cases")
async def list_test_cases(project_id: int = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(ApiTestCase).order_by(ApiTestCase.id.desc())
    if project_id:
        stmt = stmt.where(ApiTestCase.project_id == project_id)
    result = await db.execute(stmt)
    return success([{
        "id": c.id, "name": c.name, "endpoint_id": c.endpoint_id,
        "description": c.description, "priority": c.priority, "status": c.status,
    } for c in result.scalars().all()])


@router.post("/test-cases")
async def create_test_case(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    tc = ApiTestCase(
        endpoint_id=body.get("endpoint_id"), project_id=body.get("project_id"),
        name=body.get("name", ""), description=body.get("description"),
        priority=body.get("priority", "medium"), status="active",
        created_at=ts, updated_at=ts,
    )
    db.add(tc)
    await db.commit()
    await db.refresh(tc)
    return success({"id": tc.id})


# ---- Executions ----
@router.get("/executions")
async def list_executions(project_id: int = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(ApiExecution).order_by(ApiExecution.id.desc())
    if project_id:
        stmt = stmt.where(ApiExecution.project_id == project_id)
    result = await db.execute(stmt)
    return success([{
        "id": e.id, "status": e.status, "total": e.total,
        "passed": e.passed, "failed": e.failed,
        "duration_ms": e.duration_ms, "trigger_type": e.trigger_type,
        "created_at": e.created_at,
    } for e in result.scalars().all()])


@router.post("/executions")
async def create_execution(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    exe = ApiExecution(
        project_id=body.get("project_id"),
        environment_id=body.get("environment_id"),
        status="running", trigger_type=body.get("trigger_type", "manual"),
        created_at=ts, updated_at=ts,
    )
    db.add(exe)
    await db.commit()
    await db.refresh(exe)
    return success({"id": exe.id})
