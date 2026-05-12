from fastapi import APIRouter, Depends, Query, Request
import jwt
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.response import success, fail
from app.models.test_case_model import TestCase, TestCaseStep
from app.models.execution_model import TestExecution, TestExecutionResult, TestReport
from app.models.hr_model import Employee
from app.models.user_model import User
from app.util.time_utils import now_str

router = APIRouter(prefix="/test-cases", tags=["Test Cases"])
exec_router = APIRouter(prefix="/test-executions", tags=["Test Executions"])
report_router = APIRouter(prefix="/test-reports", tags=["Test Reports"])


# ---------------------------------------------------------------------------
# Test Case CRUD
# ---------------------------------------------------------------------------

@router.get("/modules")
async def list_modules(
    project_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(distinct(TestCase.module)).where(TestCase.module.isnot(None))
    if project_id:
        stmt = stmt.where(TestCase.project_id == project_id)
    result = await db.execute(stmt)
    modules = [row[0] for row in result.all() if row[0]]
    return success(modules)


@router.get("/stats/summary")
async def case_stats(
    project_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
):
    base_filter = TestCase.project_id == project_id if project_id else True

    r_total = await db.execute(select(func.count(TestCase.id)).where(base_filter))
    r_status = await db.execute(
        select(TestCase.status, func.count(TestCase.id))
        .where(base_filter).group_by(TestCase.status)
    )
    r_priority = await db.execute(
        select(TestCase.priority, func.count(TestCase.id))
        .where(base_filter).group_by(TestCase.priority)
    )
    r_module = await db.execute(
        select(TestCase.module, func.count(TestCase.id))
        .where(base_filter).group_by(TestCase.module)
    )
    return success({
        "total": int(r_total.scalar() or 0),
        "by_status": {row[0]: row[1] for row in r_status.all()},
        "by_priority": {row[0]: row[1] for row in r_priority.all()},
        "by_module": {row[0]: row[1] for row in r_module.all()},
    })


@router.get("")
async def list_cases(
    keyword: str = Query(None),
    project_id: int = Query(None),
    requirement_id: int = Query(None),
    module: str = Query(None),
    priority: str = Query(None),
    status: str = Query(None),
    source: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    base = select(TestCase)
    if project_id:
        base = base.where(TestCase.project_id == project_id)
    if requirement_id:
        base = base.where(TestCase.requirement_id == requirement_id)
    if module:
        base = base.where(TestCase.module == module)
    if priority:
        base = base.where(TestCase.priority == priority)
    if status:
        base = base.where(TestCase.status == status)
    if source:
        base = base.where(TestCase.source == source)
    if keyword:
        base = base.where(TestCase.title.ilike(f"%{keyword}%"))

    count_stmt = select(func.count()).select_from(base.subquery())
    data_stmt = (
        base.options(selectinload(TestCase.steps))
        .order_by(TestCase.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    r_count = await db.execute(count_stmt)
    total = int(r_count.scalar() or 0)
    r_data = await db.execute(data_stmt)
    items = r_data.scalars().unique().all()

    return success({
        "total": total, "page": page, "page_size": page_size,
        "items": [_case_dict(c) for c in items],
    })


@router.post("")
async def create_case(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    case = TestCase(
        title=body.get("title", ""),
        module=body.get("module"),
        priority=body.get("priority", "medium"),
        case_type=body.get("case_type", "functional"),
        precondition=body.get("precondition"),
        description=body.get("description"),
        status=body.get("status", "active"),
        source=body.get("source", "manual"),
        project_id=body.get("project_id"),
        requirement_id=body.get("requirement_id"),
        task_id=body.get("task_id"),
        assignee_id=body.get("assignee_id"),
        created_at=ts, updated_at=ts,
    )
    for s in body.get("steps") or []:
        case.steps.append(TestCaseStep(
            order=s.get("order", 0),
            action=s.get("action", ""),
            expected_result=s.get("expected_result"),
            test_data=s.get("test_data"),
            created_at=ts, updated_at=ts,
        ))
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return success({"id": case.id, "title": case.title})


@router.get("/{case_id}")
async def get_case(case_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(TestCase)
        .options(selectinload(TestCase.steps))
        .where(TestCase.id == case_id)
    )
    result = await db.execute(stmt)
    case = result.scalars().first()
    if not case:
        return fail("用例不存在")
    return success(_case_dict(case))


@router.put("/{case_id}")
async def update_case(case_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(TestCase)
        .options(selectinload(TestCase.steps))
        .where(TestCase.id == case_id)
    )
    result = await db.execute(stmt)
    case = result.scalars().first()
    if not case:
        return fail("用例不存在")

    updatable = (
        "title", "module", "priority", "case_type", "precondition",
        "description", "status", "source", "project_id", "requirement_id",
        "task_id", "assignee_id",
    )
    for field in updatable:
        if field in body:
            setattr(case, field, body[field])

    ts = now_str()
    if "steps" in body:
        case.steps.clear()
        for s in body["steps"]:
            case.steps.append(TestCaseStep(
                order=s.get("order", 0),
                action=s.get("action", ""),
                expected_result=s.get("expected_result"),
                test_data=s.get("test_data"),
                created_at=ts, updated_at=ts,
            ))
    case.updated_at = ts
    await db.commit()
    return success({"id": case.id})


@router.delete("/{case_id}")
async def delete_case(case_id: int, db: AsyncSession = Depends(get_db)):
    case = await db.get(TestCase, case_id)
    if not case:
        return fail("用例不存在")
    await db.delete(case)
    await db.commit()
    return success(None)


@router.post("/batch-adopt")
async def batch_adopt(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    created_ids = []
    created_count = 0
    updated_count = 0
    for item in body.get("cases") or []:
        title = str(item.get("title") or "").strip()
        if not title:
            continue

        stmt = (
            select(TestCase)
            .options(selectinload(TestCase.steps))
            .where(
                TestCase.task_id == item.get("task_id"),
                TestCase.title == title,
                TestCase.source == item.get("source", "ai"),
            )
        )
        if item.get("requirement_id") is not None:
            stmt = stmt.where(TestCase.requirement_id == item.get("requirement_id"))
        existing = (await db.execute(stmt)).scalars().first()

        if existing:
            case = existing
            case.steps.clear()
            updated_count += 1
        else:
            case = TestCase(created_at=ts, updated_at=ts)
            db.add(case)
            created_count += 1

        case.title = title
        case.module = item.get("module")
        case.priority = item.get("priority", "medium")
        case.case_type = item.get("case_type", "functional")
        case.precondition = item.get("precondition")
        case.description = item.get("description")
        case.status = "active"
        case.source = item.get("source", "ai")
        case.project_id = item.get("project_id")
        case.requirement_id = item.get("requirement_id")
        case.task_id = item.get("task_id")
        case.updated_at = ts
        for s in item.get("steps") or []:
            case.steps.append(TestCaseStep(
                order=s.get("order", 0),
                action=s.get("action", ""),
                expected_result=s.get("expected_result"),
                test_data=s.get("test_data"),
                created_at=ts, updated_at=ts,
            ))
        await db.flush()
        created_ids.append(case.id)
    await db.commit()
    return success({
        "count": len(created_ids),
        "ids": created_ids,
        "created": created_count,
        "updated": updated_count,
    })


def _case_dict(c: TestCase) -> dict:
    return {
        "id": c.id,
        "project_id": c.project_id,
        "requirement_id": c.requirement_id,
        "task_id": c.task_id,
        "title": c.title,
        "module": c.module,
        "priority": c.priority,
        "case_type": c.case_type,
        "description": c.description,
        "precondition": c.precondition,
        "status": c.status,
        "source": c.source,
        "assignee_id": c.assignee_id,
        "last_result": c.last_result,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "steps": [
            {
                "id": s.id,
                "order": s.order,
                "action": s.action,
                "expected_result": s.expected_result,
                "test_data": s.test_data,
            }
            for s in sorted(c.steps, key=lambda x: x.order)
        ],
    }


# ---------------------------------------------------------------------------
# Test Execution
# ---------------------------------------------------------------------------

@exec_router.get("")
async def list_executions(
    project_id: int = Query(None),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    base = select(TestExecution)
    if project_id:
        base = base.where(TestExecution.project_id == project_id)
    if status:
        base = base.where(TestExecution.status == status)

    count_stmt = select(func.count()).select_from(base.subquery())
    data_stmt = base.order_by(TestExecution.id.desc()).offset((page - 1) * page_size).limit(page_size)

    r_count = await db.execute(count_stmt)
    total = int(r_count.scalar() or 0)
    r_data = await db.execute(data_stmt)
    items = r_data.scalars().all()
    executor_names = await _executor_name_map(db, [e.executor_id for e in items if e.executor_id])

    return success({
        "total": total, "page": page, "page_size": page_size,
        "items": [_exec_dict(e, executor_names) for e in items],
    })


@exec_router.post("")
async def create_execution(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ts = now_str()
    case_ids = body.get("case_ids") or []
    executor_id = body.get("executor_id") or await _current_user_id(request, db)
    execution = TestExecution(
        title=body.get("title", ""),
        project_id=body.get("project_id"),
        plan_type=body.get("plan_type", "manual"),
        status="pending",
        total_cases=len(case_ids),
        passed_cases=0, failed_cases=0, blocked_cases=0, skipped_cases=0,
        executor_id=executor_id,
        created_at=ts, updated_at=ts,
    )
    db.add(execution)
    await db.flush()

    for cid in case_ids:
        db.add(TestExecutionResult(
            execution_id=execution.id,
            test_case_id=cid,
            status="pending",
            executor_id=executor_id,
            created_at=ts, updated_at=ts,
        ))
    await db.commit()
    await db.refresh(execution)
    return success({"id": execution.id, "title": execution.title, "total_cases": execution.total_cases})


@exec_router.put("/{exec_id}")
async def update_execution(exec_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    execution = await db.get(TestExecution, exec_id)
    if not execution:
        return fail("执行计划不存在")

    for field in ("title", "project_id", "plan_type", "executor_id"):
        if field in body:
            setattr(execution, field, body[field])
    execution.updated_at = now_str()
    await db.commit()
    names = await _executor_name_map(db, [execution.executor_id] if execution.executor_id else [])
    return success(_exec_dict(execution, names))


@exec_router.get("/{exec_id}")
async def get_execution(exec_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(TestExecution)
        .options(selectinload(TestExecution.results))
        .where(TestExecution.id == exec_id)
    )
    result = await db.execute(stmt)
    execution = result.scalars().first()
    if not execution:
        return fail("执行计划不存在")

    case_ids = [r.test_case_id for r in execution.results]
    case_map: dict[int, dict] = {}
    if case_ids:
        case_result = await db.execute(
            select(TestCase.id, TestCase.title, TestCase.module, TestCase.priority).where(TestCase.id.in_(case_ids))
        )
        case_map = {
            row[0]: {"title": row[1], "module": row[2], "priority": row[3]}
            for row in case_result.all()
        }

    names = await _executor_name_map(db, [execution.executor_id] if execution.executor_id else [])
    data = _exec_dict(execution, names)
    data["results"] = [
        {
            "id": r.id,
            "test_case_id": r.test_case_id,
            "test_case_title": case_map.get(r.test_case_id, {}).get("title", ""),
            "test_case_module": case_map.get(r.test_case_id, {}).get("module"),
            "test_case_priority": case_map.get(r.test_case_id, {}).get("priority"),
            "status": r.status,
            "actual_result": r.actual_result,
            "notes": r.notes,
            "executed_at": r.executed_at,
            "executor_id": r.executor_id,
        }
        for r in execution.results
    ]
    return success(data)


@exec_router.put("/{exec_id}/cases")
async def update_execution_cases(exec_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(TestExecution)
        .options(selectinload(TestExecution.results))
        .where(TestExecution.id == exec_id)
    )
    result = await db.execute(stmt)
    execution = result.scalars().first()
    if not execution:
        return fail("执行计划不存在")

    incoming_ids = [int(cid) for cid in body.get("case_ids") or [] if cid]
    existing_ids = {r.test_case_id for r in execution.results}
    ts = now_str()
    added = 0
    for cid in incoming_ids:
        if cid in existing_ids:
            continue
        db.add(TestExecutionResult(
            execution_id=execution.id,
            test_case_id=cid,
            status="pending",
            executor_id=execution.executor_id,
            created_at=ts,
            updated_at=ts,
        ))
        existing_ids.add(cid)
        added += 1

    execution.total_cases = len(existing_ids)
    execution.updated_at = ts
    await db.commit()
    return success({"id": execution.id, "added": added, "total_cases": execution.total_cases})


@exec_router.put("/{exec_id}/results/{result_id}")
async def update_result(
    exec_id: int, result_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    res = await db.get(TestExecutionResult, result_id)
    if not res or res.execution_id != exec_id:
        return fail("执行结果不存在")

    ts = now_str()
    new_status = body.get("status", res.status)
    res.status = new_status
    if "actual_result" in body:
        res.actual_result = body["actual_result"]
    if "notes" in body:
        res.notes = body["notes"]
    if "executor_id" in body:
        res.executor_id = body["executor_id"]
    res.executed_at = ts
    res.updated_at = ts

    stmt = (
        select(TestExecution)
        .options(selectinload(TestExecution.results))
        .where(TestExecution.id == exec_id)
    )
    r = await db.execute(stmt)
    execution = r.scalars().first()
    if execution:
        all_results = execution.results
        execution.passed_cases = sum(1 for x in all_results if x.status == "passed")
        execution.failed_cases = sum(1 for x in all_results if x.status == "failed")
        execution.blocked_cases = sum(1 for x in all_results if x.status == "blocked")
        execution.skipped_cases = sum(1 for x in all_results if x.status == "skipped")

        done = all(x.status != "pending" for x in all_results)
        if done and execution.status == "running":
            execution.status = "completed"
            execution.completed_at = ts
        execution.updated_at = ts

    # Update last_result on the test case
    case = await db.get(TestCase, res.test_case_id)
    if case:
        case.last_result = new_status
        case.updated_at = ts

    await db.commit()
    return success({"id": res.id, "status": res.status})


@exec_router.put("/{exec_id}/start")
async def start_execution(exec_id: int, db: AsyncSession = Depends(get_db)):
    execution = await db.get(TestExecution, exec_id)
    if not execution:
        return fail("执行计划不存在")
    execution.status = "running"
    execution.started_at = now_str()
    execution.updated_at = execution.started_at
    await db.commit()
    return success({"id": execution.id, "status": execution.status})


@exec_router.put("/{exec_id}/abort")
async def abort_execution(exec_id: int, db: AsyncSession = Depends(get_db)):
    execution = await db.get(TestExecution, exec_id)
    if not execution:
        return fail("执行计划不存在")
    execution.status = "aborted"
    execution.updated_at = now_str()
    await db.commit()
    return success({"id": execution.id, "status": execution.status})


@exec_router.delete("/{exec_id}")
async def delete_execution(exec_id: int, db: AsyncSession = Depends(get_db)):
    execution = await db.get(TestExecution, exec_id)
    if not execution:
        return fail("执行计划不存在")
    await db.delete(execution)
    await db.commit()
    return success(None)


@exec_router.post("/{exec_id}/report")
async def generate_report(exec_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(TestExecution)
        .options(selectinload(TestExecution.results))
        .where(TestExecution.id == exec_id)
    )
    r = await db.execute(stmt)
    execution = r.scalars().first()
    if not execution:
        return fail("执行计划不存在")

    total = execution.total_cases or len(execution.results)
    passed = sum(1 for x in execution.results if x.status == "passed")
    failed = sum(1 for x in execution.results if x.status == "failed")
    blocked = sum(1 for x in execution.results if x.status == "blocked")
    skipped = sum(1 for x in execution.results if x.status == "skipped")
    pass_rate = round(passed / total * 100, 2) if total > 0 else 0.0

    ts = now_str()
    report = TestReport(
        execution_id=exec_id,
        title=f"{execution.title} - 测试报告",
        summary=f"共 {total} 条用例，通过 {passed}，失败 {failed}，阻塞 {blocked}，跳过 {skipped}，通过率 {pass_rate}%",
        total_cases=total,
        passed_cases=passed,
        failed_cases=failed,
        blocked_cases=blocked,
        skipped_cases=skipped,
        pass_rate=pass_rate,
        generated_at=ts,
        created_at=ts, updated_at=ts,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return success(_report_dict(report))


def _exec_dict(e: TestExecution, executor_names: dict[int, str] | None = None) -> dict:
    executor_names = executor_names or {}
    return {
        "id": e.id,
        "title": e.title,
        "project_id": e.project_id,
        "plan_type": e.plan_type,
        "status": e.status,
        "total_cases": e.total_cases,
        "passed_cases": e.passed_cases,
        "failed_cases": e.failed_cases,
        "blocked_cases": e.blocked_cases,
        "skipped_cases": e.skipped_cases,
        "executor_id": e.executor_id,
        "executor_name": executor_names.get(e.executor_id) if e.executor_id else None,
        "started_at": e.started_at,
        "completed_at": e.completed_at,
        "created_at": e.created_at,
        "updated_at": e.updated_at,
    }


async def _current_user_id(request: Request, db: AsyncSession) -> int | None:
    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(
            auth_header.removeprefix("Bearer ").strip(),
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.InvalidTokenError:
        return None
    username = payload.get("username") or payload.get("sub")
    if not username:
        return None
    result = await db.execute(select(User.id).where(User.username == username))
    return result.scalar_one_or_none()


async def _executor_name_map(db: AsyncSession, user_ids: list[int]) -> dict[int, str]:
    ids = sorted({uid for uid in user_ids if uid})
    if not ids:
        return {}

    result = await db.execute(select(User.id, User.username).where(User.id.in_(ids)))
    names = {row[0]: row[1] for row in result.all()}

    employee_result = await db.execute(
        select(Employee.user_id, Employee.name).where(Employee.user_id.in_(ids))
    )
    for user_id, name in employee_result.all():
        if name:
            names[user_id] = name
    return names


# ---------------------------------------------------------------------------
# Test Reports
# ---------------------------------------------------------------------------

@report_router.get("")
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    base = select(TestReport)
    count_stmt = select(func.count()).select_from(base.subquery())
    data_stmt = base.order_by(TestReport.id.desc()).offset((page - 1) * page_size).limit(page_size)

    r_count = await db.execute(count_stmt)
    total = int(r_count.scalar() or 0)
    r_data = await db.execute(data_stmt)
    items = r_data.scalars().all()

    return success({
        "total": total, "page": page, "page_size": page_size,
        "items": [_report_dict(r) for r in items],
    })


@report_router.get("/{report_id}")
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(TestReport)
        .options(selectinload(TestReport.execution))
        .where(TestReport.id == report_id)
    )
    result = await db.execute(stmt)
    report = result.scalars().first()
    if not report:
        return fail("报告不存在")

    data = _report_dict(report)
    if report.execution:
        data["execution"] = _exec_dict(report.execution)
    return success(data)


def _report_dict(r: TestReport) -> dict:
    return {
        "id": r.id,
        "execution_id": r.execution_id,
        "title": r.title,
        "summary": r.summary,
        "total_cases": r.total_cases,
        "passed_cases": r.passed_cases,
        "failed_cases": r.failed_cases,
        "blocked_cases": r.blocked_cases,
        "skipped_cases": r.skipped_cases,
        "pass_rate": r.pass_rate,
        "generated_at": r.generated_at,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }
