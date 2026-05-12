from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success, fail
from app.models.performance_model import PerfScenario, PerfScript, PerfExecution, PerfResult, PerfBaseline
from app.util.time_utils import now_str

router = APIRouter(prefix="/performance", tags=["Performance"])


# ---- Scenarios ----
@router.get("/scenarios")
async def list_scenarios(project_id: int = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(PerfScenario).order_by(PerfScenario.id.desc())
    if project_id:
        stmt = stmt.where(PerfScenario.project_id == project_id)
    result = await db.execute(stmt)
    return success([{
        "id": s.id, "name": s.name, "description": s.description,
        "test_type": s.test_type, "target_url": s.target_url,
        "concurrency": s.concurrency, "duration_seconds": s.duration_seconds,
        "status": s.status, "created_at": s.created_at,
    } for s in result.scalars().all()])


@router.post("/scenarios")
async def create_scenario(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    scenario = PerfScenario(
        project_id=body.get("project_id"), name=body.get("name", ""),
        description=body.get("description"), test_type=body.get("test_type", "load"),
        target_url=body.get("target_url"), concurrency=body.get("concurrency"),
        duration_seconds=body.get("duration_seconds"),
        ramp_up_seconds=body.get("ramp_up_seconds"),
        status="draft", created_at=ts, updated_at=ts,
    )
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    return success({"id": scenario.id})


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: int, db: AsyncSession = Depends(get_db)):
    s = await db.get(PerfScenario, scenario_id)
    if not s:
        return fail("场景不存在")
    return success({
        "id": s.id, "name": s.name, "description": s.description,
        "test_type": s.test_type, "target_url": s.target_url,
        "concurrency": s.concurrency, "duration_seconds": s.duration_seconds,
        "ramp_up_seconds": s.ramp_up_seconds, "status": s.status,
    })


@router.put("/scenarios/{scenario_id}")
async def update_scenario(scenario_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    s = await db.get(PerfScenario, scenario_id)
    if not s:
        return fail("场景不存在")
    for field in ("name", "description", "test_type", "target_url", "concurrency", "duration_seconds", "ramp_up_seconds", "status"):
        if field in body:
            setattr(s, field, body[field])
    s.updated_at = now_str()
    await db.commit()
    return success({"id": s.id})


@router.delete("/scenarios/{scenario_id}")
async def delete_scenario(scenario_id: int, db: AsyncSession = Depends(get_db)):
    s = await db.get(PerfScenario, scenario_id)
    if not s:
        return fail("场景不存在")
    await db.delete(s)
    await db.commit()
    return success(None)


# ---- Scripts ----
@router.get("/scenarios/{scenario_id}/scripts")
async def list_scripts(scenario_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PerfScript).where(PerfScript.scenario_id == scenario_id)
    )
    return success([{
        "id": s.id, "name": s.name, "script_type": s.script_type,
        "content": s.content, "file_path": s.file_path,
    } for s in result.scalars().all()])


@router.post("/scenarios/{scenario_id}/scripts")
async def create_script(scenario_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    script = PerfScript(
        scenario_id=scenario_id, name=body.get("name", ""),
        script_type=body.get("script_type", "k6"),
        content=body.get("content"), file_path=body.get("file_path"),
        created_at=ts, updated_at=ts,
    )
    db.add(script)
    await db.commit()
    return success({"id": script.id})


# ---- Executions ----
@router.get("/executions")
async def list_executions(scenario_id: int = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(PerfExecution).order_by(PerfExecution.id.desc())
    if scenario_id:
        stmt = stmt.where(PerfExecution.scenario_id == scenario_id)
    result = await db.execute(stmt)
    return success([{
        "id": e.id, "scenario_id": e.scenario_id, "status": e.status,
        "started_at": e.started_at, "finished_at": e.finished_at,
        "summary_json": e.summary_json, "created_at": e.created_at,
    } for e in result.scalars().all()])


# ---- Baselines ----
@router.get("/baselines")
async def list_baselines(scenario_id: int = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(PerfBaseline).order_by(PerfBaseline.id.desc())
    if scenario_id:
        stmt = stmt.where(PerfBaseline.scenario_id == scenario_id)
    result = await db.execute(stmt)
    return success([{
        "id": b.id, "scenario_id": b.scenario_id, "name": b.name,
        "avg_response_ms": b.avg_response_ms, "p95_response_ms": b.p95_response_ms,
        "max_tps": b.max_tps, "max_error_rate": b.max_error_rate,
    } for b in result.scalars().all()])


@router.post("/baselines")
async def create_baseline(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    baseline = PerfBaseline(
        scenario_id=body.get("scenario_id"), name=body.get("name", ""),
        avg_response_ms=body.get("avg_response_ms"),
        p95_response_ms=body.get("p95_response_ms"),
        max_tps=body.get("max_tps"), max_error_rate=body.get("max_error_rate"),
        created_at=ts, updated_at=ts,
    )
    db.add(baseline)
    await db.commit()
    return success({"id": baseline.id})
