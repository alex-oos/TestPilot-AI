import os
import uuid

from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success, fail
from app.models.defect_model import Defect, DefectComment, DefectHistory
from app.util.time_utils import now_str

router = APIRouter(prefix="/defects", tags=["Defects"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads", "editor")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload/image")
async def upload_editor_image(file: UploadFile = File(...)):
    """富文本编辑器内联图片上传"""
    ext = os.path.splitext(file.filename or "")[1] or ".png"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    content = await file.read()
    with open(file_path, "wb") as fp:
        fp.write(content)
    url = f"/uploads/editor/{unique_name}"
    return {"errno": 0, "data": {"url": url}}


@router.get("")
async def list_defects(
    project_id: int = Query(None),
    status: str = Query(None),
    severity: str = Query(None),
    assignee_id: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    base = select(Defect)
    if project_id:
        base = base.where(Defect.project_id == project_id)
    if status:
        base = base.where(Defect.status == status)
    if severity:
        base = base.where(Defect.severity == severity)
    if assignee_id:
        base = base.where(Defect.assignee_id == assignee_id)

    count_stmt = select(func.count()).select_from(base.subquery())
    data_stmt = base.order_by(Defect.id.desc()).offset((page - 1) * page_size).limit(page_size)

    r_count = await db.execute(count_stmt)
    total = int(r_count.scalar() or 0)
    r_data = await db.execute(data_stmt)
    items = r_data.scalars().all()

    return success({
        "total": total, "page": page, "page_size": page_size,
        "items": [{
            "id": d.id, "project_id": d.project_id, "title": d.title,
            "severity": d.severity, "priority": d.priority, "status": d.status,
            "defect_type": d.defect_type, "module": d.module,
            "reporter_id": d.reporter_id, "assignee_id": d.assignee_id,
            "created_at": d.created_at, "updated_at": d.updated_at,
        } for d in items],
    })


@router.post("")
async def create_defect(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    defect = Defect(
        project_id=body.get("project_id"), title=body.get("title", ""),
        description=body.get("description"), severity=body.get("severity", "medium"),
        priority=body.get("priority", "medium"), status="open",
        defect_type=body.get("defect_type", "functional"), module=body.get("module"),
        reporter_id=body.get("reporter_id"), assignee_id=body.get("assignee_id"),
        requirement_id=body.get("requirement_id"), version_id=body.get("version_id"),
        environment=body.get("environment"),
        steps_to_reproduce=body.get("steps_to_reproduce"),
        expected_result=body.get("expected_result"),
        actual_result=body.get("actual_result"),
        created_at=ts, updated_at=ts,
    )
    db.add(defect)
    await db.commit()
    await db.refresh(defect)
    return success({"id": defect.id, "title": defect.title})


@router.get("/stats/summary")
async def defect_stats(project_id: int = Query(None), db: AsyncSession = Depends(get_db)):
    base_filter = Defect.project_id == project_id if project_id else True

    stmt_status = (
        select(Defect.status, func.count(Defect.id))
        .where(base_filter).group_by(Defect.status)
    )
    stmt_severity = (
        select(Defect.severity, func.count(Defect.id))
        .where(base_filter).group_by(Defect.severity)
    )
    stmt_total = select(func.count(Defect.id)).where(base_filter)

    r_status = await db.execute(stmt_status)
    r_severity = await db.execute(stmt_severity)
    r_total = await db.execute(stmt_total)

    return success({
        "total": int(r_total.scalar() or 0),
        "by_status": {row[0]: row[1] for row in r_status.all()},
        "by_severity": {row[0]: row[1] for row in r_severity.all()},
    })


@router.get("/{defect_id}")
async def get_defect(defect_id: int, db: AsyncSession = Depends(get_db)):
    defect = await db.get(Defect, defect_id)
    if not defect:
        return fail("缺陷不存在")
    return success({
        "id": defect.id, "project_id": defect.project_id, "title": defect.title,
        "description": defect.description, "severity": defect.severity,
        "priority": defect.priority, "status": defect.status,
        "defect_type": defect.defect_type, "module": defect.module,
        "reporter_id": defect.reporter_id, "assignee_id": defect.assignee_id,
        "steps_to_reproduce": defect.steps_to_reproduce,
        "expected_result": defect.expected_result,
        "actual_result": defect.actual_result,
        "environment": defect.environment,
        "created_at": defect.created_at, "resolved_at": defect.resolved_at,
    })


@router.put("/{defect_id}")
async def update_defect(defect_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    defect = await db.get(Defect, defect_id)
    if not defect:
        return fail("缺陷不存在")
    updatable = (
        "title", "description", "severity", "priority", "status",
        "defect_type", "module", "assignee_id", "environment",
        "steps_to_reproduce", "expected_result", "actual_result",
    )
    ts = now_str()
    for field in updatable:
        if field in body:
            old_val = getattr(defect, field)
            new_val = body[field]
            if old_val != new_val:
                db.add(DefectHistory(
                    defect_id=defect_id, field=field,
                    old_value=str(old_val) if old_val else None,
                    new_value=str(new_val) if new_val else None,
                    created_at=ts, updated_at=ts,
                ))
                setattr(defect, field, new_val)
    if body.get("status") == "resolved" and not defect.resolved_at:
        defect.resolved_at = ts
    if body.get("status") == "closed" and not defect.closed_at:
        defect.closed_at = ts
    defect.updated_at = ts
    await db.commit()
    return success({"id": defect.id})


@router.delete("/{defect_id}")
async def delete_defect(defect_id: int, db: AsyncSession = Depends(get_db)):
    defect = await db.get(Defect, defect_id)
    if not defect:
        return fail("缺陷不存在")
    await db.delete(defect)
    await db.commit()
    return success(None)


@router.get("/{defect_id}/comments")
async def list_comments(defect_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DefectComment).where(DefectComment.defect_id == defect_id).order_by(DefectComment.id)
    )
    return success([{
        "id": c.id, "user_id": c.user_id, "content": c.content, "created_at": c.created_at,
    } for c in result.scalars().all()])


@router.post("/{defect_id}/comments")
async def add_comment(defect_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    comment = DefectComment(
        defect_id=defect_id, user_id=body.get("user_id"),
        content=body.get("content", ""), created_at=ts, updated_at=ts,
    )
    db.add(comment)
    await db.commit()
    return success({"id": comment.id})


@router.get("/{defect_id}/history")
async def list_history(defect_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DefectHistory).where(DefectHistory.defect_id == defect_id).order_by(DefectHistory.id)
    )
    return success([{
        "id": h.id, "field": h.field, "old_value": h.old_value,
        "new_value": h.new_value, "created_at": h.created_at,
    } for h in result.scalars().all()])

