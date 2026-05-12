import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success, fail
from app.models.project_model import Project
from app.models.requirement_model import Requirement, RequirementTrace, RequirementNodeMember
from app.models.hr_model import Employee, Schedule
from app.util.time_utils import now_str

FINAL_REQ_NODE = "regression"

router = APIRouter(prefix="/requirements", tags=["Requirements"])


@router.get("")
async def list_requirements(
    project_id: int = Query(None),
    status: str = Query(None),
    priority: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    base = select(Requirement)
    if project_id:
        base = base.where(Requirement.project_id == project_id)
    if status:
        base = base.where(Requirement.status == status)
    if priority:
        base = base.where(Requirement.priority == priority)

    count_stmt = select(func.count()).select_from(base.subquery())
    data_stmt = base.order_by(Requirement.id.desc()).offset((page - 1) * page_size).limit(page_size)

    r_count = await db.execute(count_stmt)
    total = int(r_count.scalar() or 0)
    r_data = await db.execute(data_stmt)
    items = r_data.scalars().all()

    return success({
        "total": total, "page": page, "page_size": page_size,
        "items": [{
            "id": r.id, "project_id": r.project_id, "title": r.title,
            "description": r.description, "priority": r.priority,
            "status": r.status, "req_type": r.req_type,
            "assignee_id": r.assignee_id, "source": r.source,
            "product_owner_id": r.product_owner_id,
            "dev_owner_id": r.dev_owner_id,
            "test_owner_id": r.test_owner_id,
            "created_at": r.created_at, "updated_at": r.updated_at,
        } for r in items],
    })


@router.post("")
async def create_requirement(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    project_activated = False

    pid = body.get("project_id")
    if pid:
        project = await db.get(Project, pid)
        if not project:
            return fail("项目不存在")
        if project.status not in ("approved", "active"):
            label = {"draft": "草稿", "archived": "已归档", "suspended": "暂停"}.get(project.status, project.status)
            return fail(f"项目当前为「{label}」状态，无法创建需求")
        if project.status == "approved":
            project.status = "active"
            project.updated_at = ts
            project_activated = True

    req = Requirement(
        project_id=pid, title=body.get("title", ""),
        description=body.get("description"), priority=body.get("priority", "medium"),
        status=body.get("status", "requirement_review"), req_type=body.get("req_type", "functional"),
        version_id=body.get("version_id"), assignee_id=body.get("assignee_id"),
        source=body.get("source"),
        product_owner_id=body.get("product_owner_id"),
        dev_owner_id=body.get("dev_owner_id"),
        test_owner_id=body.get("test_owner_id"),
        created_at=ts, updated_at=ts,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return success({"id": req.id, "title": req.title, "project_activated": project_activated})


@router.get("/{req_id}")
async def get_requirement(req_id: int, db: AsyncSession = Depends(get_db)):
    req = await db.get(Requirement, req_id)
    if not req:
        return fail("需求不存在")
    return success({
        "id": req.id, "project_id": req.project_id, "title": req.title,
        "description": req.description, "priority": req.priority,
        "status": req.status, "req_type": req.req_type,
        "version_id": req.version_id, "assignee_id": req.assignee_id,
        "source": req.source,
        "product_owner_id": req.product_owner_id,
        "dev_owner_id": req.dev_owner_id,
        "test_owner_id": req.test_owner_id,
        "created_at": req.created_at,
    })


@router.put("/{req_id}")
async def update_requirement(req_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    req = await db.get(Requirement, req_id)
    if not req:
        return fail("需求不存在")
    for field in ("title", "description", "priority", "status", "req_type", "assignee_id", "source", "version_id", "project_id", "product_owner_id", "dev_owner_id", "test_owner_id"):
        if field in body:
            setattr(req, field, body[field])
    req.updated_at = now_str()
    await db.commit()

    auto_archived = False
    if body.get("status") == FINAL_REQ_NODE and req.project_id:
        all_reqs = await db.execute(
            select(Requirement.status).where(Requirement.project_id == req.project_id)
        )
        statuses = [r[0] for r in all_reqs.all()]
        if statuses and all(s == FINAL_REQ_NODE for s in statuses):
            project = await db.get(Project, req.project_id)
            if project and project.status == "active":
                project.status = "archived"
                project.updated_at = now_str()
                await db.commit()
                auto_archived = True

    return success({"id": req.id, "auto_archived": auto_archived})


@router.delete("/{req_id}")
async def delete_requirement(req_id: int, db: AsyncSession = Depends(get_db)):
    req = await db.get(Requirement, req_id)
    if not req:
        return fail("需求不存在")
    await db.delete(req)
    await db.commit()
    return success(None)


@router.get("/{req_id}/traces")
async def list_traces(req_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RequirementTrace).where(RequirementTrace.requirement_id == req_id)
    )
    return success([{
        "id": t.id, "target_type": t.target_type,
        "target_id": t.target_id, "relation": t.relation,
    } for t in result.scalars().all()])


# ---- 节点人员管理 ----
@router.get("/{req_id}/node-members")
async def list_node_members(req_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RequirementNodeMember).where(RequirementNodeMember.requirement_id == req_id)
    )
    members = result.scalars().all()

    emp_ids = list({m.employee_id for m in members})
    emp_map = {}
    if emp_ids:
        emp_result = await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))
        for e in emp_result.scalars().all():
            emp_map[e.id] = {"id": e.id, "name": e.name, "role": e.role, "level": e.level, "email": e.email}

    return success([{
        "id": m.id, "node": m.node, "role": m.role,
        "employee_id": m.employee_id,
        "employee": emp_map.get(m.employee_id),
        "planned_time": m.planned_time,
    } for m in members])


NODE_LABEL = {
    "requirement_review": "需求评审", "tech_review": "技术评审",
    "case_review": "用例评审", "testing": "测试执行",
    "acceptance": "验收测试", "released": "发布上线", "regression": "线上回归",
}


@router.put("/{req_id}/node-members/{node}")
async def save_node_members(req_id: int, node: str, body: dict, db: AsyncSession = Depends(get_db)):
    """整体保存某个节点的人员配置，并自动同步排期日历"""
    req = await db.get(Requirement, req_id)
    if not req:
        return fail("需求不存在")

    await db.execute(
        sa_delete(RequirementNodeMember).where(
            RequirementNodeMember.requirement_id == req_id,
            RequirementNodeMember.node == node,
        )
    )

    ts = now_str()
    members_data = body.get("members", [])
    planned_time = body.get("planned_time", "")
    created = []
    for m in members_data:
        nm = RequirementNodeMember(
            requirement_id=req_id, node=node,
            role=m.get("role", ""), employee_id=m.get("employee_id"),
            planned_time=planned_time,
            created_at=ts, updated_at=ts,
        )
        db.add(nm)
        created.append(nm)
    await db.commit()

    # ---- 自动同步排期日历 ----
    source_tag = f"[req_node:{req_id}:{node}]"
    old_scheds = await db.execute(
        select(Schedule).where(Schedule.description.like(f"{source_tag}%"))
    )
    for s in old_scheds.scalars().all():
        await db.delete(s)
    await db.flush()

    if planned_time and members_data:
        parts = planned_time.split("~")
        if len(parts) < 2:
            parts = planned_time.split(" - ")
        if len(parts) == 2:
            try:
                start_dt = datetime.strptime(parts[0].strip(), "%Y-%m-%d")
                end_dt = datetime.strptime(parts[1].strip(), "%Y-%m-%d")
            except ValueError:
                start_dt = end_dt = None

            if start_dt and end_dt:
                node_label = NODE_LABEL.get(node, node)
                emp_ids = list({m.get("employee_id") for m in members_data if m.get("employee_id")})
                current = start_dt
                while current <= end_dt:
                    date_str = current.strftime("%Y-%m-%d")
                    if current.weekday() < 5:  # skip weekends
                        for eid in emp_ids:
                            schedule = Schedule(
                                employee_id=eid,
                                project_id=req.project_id,
                                title=f"{req.title} - {node_label}",
                                schedule_date=date_str,
                                schedule_type="work",
                                description=f"{source_tag} 需求#{req_id}",
                                created_at=ts, updated_at=ts,
                            )
                            db.add(schedule)
                    current += timedelta(days=1)
                await db.commit()

    return success({"node": node, "count": len(created)})
