from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success, fail
from app.models.project_model import Project, ProjectMember, ProjectVersion
from app.models.requirement_model import Requirement, RequirementNodeMember
from app.models.hr_model import Employee
from app.util.time_utils import now_str

router = APIRouter(prefix="/projects", tags=["Projects"])

PROJECT_STATUS = ("draft", "approved", "active", "archived", "suspended")
PROJECT_STATUS_LABEL = {
    "draft": "草稿", "approved": "已立项",
    "active": "进行中", "archived": "已归档", "suspended": "暂停",
}


async def _resolve_owner(db: AsyncSession, owner_id: int | None) -> dict | None:
    if not owner_id:
        return None
    result = await db.execute(select(Employee).where(Employee.id == owner_id))
    e = result.scalar()
    if not e:
        return None
    return {"id": e.id, "name": e.name, "position": e.position}


async def _project_dict(p: Project, db: AsyncSession) -> dict:
    owner = await _resolve_owner(db, p.owner_id)
    return {
        "id": p.id, "name": p.name, "description": p.description,
        "status": p.status, "status_label": PROJECT_STATUS_LABEL.get(p.status, p.status),
        "owner_id": p.owner_id,
        "owner_name": owner["name"] if owner else None,
        "owner": owner,
        "created_at": p.created_at, "updated_at": p.updated_at,
    }


@router.get("")
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    base = select(Project)
    if status:
        base = base.where(Project.status == status)

    count_stmt = select(func.count()).select_from(base.subquery())
    data_stmt = base.order_by(Project.id.desc()).offset((page - 1) * page_size).limit(page_size)

    r_count = await db.execute(count_stmt)
    total = int(r_count.scalar() or 0)
    r_data = await db.execute(data_stmt)
    projects = r_data.scalars().all()

    items = []
    for p in projects:
        items.append(await _project_dict(p, db))

    return success({
        "total": total, "page": page, "page_size": page_size,
        "items": items,
    })


@router.post("")
async def create_project(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    project = Project(
        name=body.get("name", ""),
        description=body.get("description"),
        status=body.get("status", "active"),
        owner_id=body.get("owner_id"),
        created_at=ts, updated_at=ts,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return success({"id": project.id, "name": project.name})


@router.get("/meta/statuses")
async def project_statuses():
    return success([{"value": s, "label": PROJECT_STATUS_LABEL[s]} for s in PROJECT_STATUS])


@router.get("/{project_id}")
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        return fail("项目不存在")
    return success(await _project_dict(project, db))


@router.put("/{project_id}")
async def update_project(project_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        return fail("项目不存在")
    for field in ("name", "description", "status", "owner_id"):
        if field in body:
            setattr(project, field, body[field])
    project.updated_at = now_str()
    await db.commit()
    return success({"id": project.id})


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        return fail("项目不存在")
    await db.delete(project)
    await db.commit()
    return success(None)


@router.get("/{project_id}/versions")
async def list_versions(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProjectVersion).where(ProjectVersion.project_id == project_id).order_by(ProjectVersion.id.desc())
    )
    return success([{
        "id": v.id, "name": v.name, "description": v.description,
        "status": v.status, "start_date": v.start_date, "end_date": v.end_date,
    } for v in result.scalars().all()])


@router.post("/{project_id}/versions")
async def create_version(project_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    version = ProjectVersion(
        project_id=project_id, name=body.get("name", ""),
        description=body.get("description"), status=body.get("status", "planning"),
        start_date=body.get("start_date"), end_date=body.get("end_date"),
        created_at=ts, updated_at=ts,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return success({"id": version.id})


@router.get("/{project_id}/members")
async def list_members(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProjectMember).where(ProjectMember.project_id == project_id)
    )
    members = result.scalars().all()

    emp_ids = [m.employee_id for m in members if getattr(m, 'employee_id', None)]
    employees_map = {}
    if emp_ids:
        emp_result = await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))
        for e in emp_result.scalars().all():
            employees_map[e.id] = {
                "id": e.id, "name": e.name,
                "position": e.position, "role": e.role, "department": e.department,
            }

    return success([{
        "id": m.id,
        "user_id": m.user_id,
        "employee_id": getattr(m, 'employee_id', None),
        "role": m.role,
        "employee": employees_map.get(getattr(m, 'employee_id', None)),
    } for m in members])


@router.post("/{project_id}/members")
async def add_member(project_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    employee_id = body.get("employee_id")
    if employee_id:
        existing = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.employee_id == employee_id,
            )
        )
        if existing.scalar():
            return fail("该成员已在项目中")

    ts = now_str()
    member = ProjectMember(
        project_id=project_id,
        user_id=body.get("user_id"),
        employee_id=employee_id,
        role=body.get("role", "developer"),
        created_at=ts, updated_at=ts,
    )
    db.add(member)
    await db.commit()
    return success({"id": member.id})


@router.delete("/{project_id}/members/{member_id}")
async def remove_member(project_id: int, member_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProjectMember).where(ProjectMember.id == member_id, ProjectMember.project_id == project_id)
    )
    member = result.scalar()
    if not member:
        return fail("成员不存在")
    await db.delete(member)
    await db.commit()
    return success(None)


# ---------------------------------------------------------------------------
# 测试排期 —— 聚合项目下所有需求的节点排期
# ---------------------------------------------------------------------------

NODE_LABEL = {
    "requirement_review": "需求评审", "tech_review": "技术评审",
    "case_review": "用例评审", "testing": "测试执行",
    "acceptance": "验收测试", "released": "发布上线", "regression": "线上回归",
}

NODE_ORDER = list(NODE_LABEL.keys())


def _parse_planned_range(raw: str | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    parts = raw.split("~") if "~" in raw else raw.split(" - ")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return None, None


@router.get("/{project_id}/test-schedule")
async def project_test_schedule(project_id: int, db: AsyncSession = Depends(get_db)):
    """聚合该项目下所有需求的流程节点排期，返回甘特图数据"""
    reqs_result = await db.execute(
        select(Requirement).where(Requirement.project_id == project_id).order_by(Requirement.id)
    )
    reqs = reqs_result.scalars().all()
    if not reqs:
        return success({"requirements": [], "date_range": None})

    req_ids = [r.id for r in reqs]
    nm_result = await db.execute(
        select(RequirementNodeMember).where(RequirementNodeMember.requirement_id.in_(req_ids))
    )
    all_members = nm_result.scalars().all()

    emp_ids = list({m.employee_id for m in all_members})
    emp_map: dict[int, dict] = {}
    if emp_ids:
        emp_result = await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))
        for e in emp_result.scalars().all():
            emp_map[e.id] = {"id": e.id, "name": e.name, "role": e.role, "position": e.position}

    members_by_req: dict[int, list] = {}
    for m in all_members:
        members_by_req.setdefault(m.requirement_id, []).append(m)

    global_min_date: str | None = None
    global_max_date: str | None = None

    items = []
    for req in reqs:
        nodes_data = []
        req_members = members_by_req.get(req.id, [])

        nodes_grouped: dict[str, list] = {}
        for m in req_members:
            nodes_grouped.setdefault(m.node, []).append(m)

        for node_key in NODE_ORDER:
            node_members = nodes_grouped.get(node_key, [])
            if not node_members:
                continue
            sample = node_members[0]
            start, end = _parse_planned_range(sample.planned_time)
            if start and end:
                if not global_min_date or start < global_min_date:
                    global_min_date = start
                if not global_max_date or end > global_max_date:
                    global_max_date = end

            people = []
            for m in node_members:
                emp = emp_map.get(m.employee_id)
                people.append({
                    "employee_id": m.employee_id,
                    "name": emp["name"] if emp else "未知",
                    "role": m.role,
                })

            nodes_data.append({
                "node": node_key,
                "node_label": NODE_LABEL.get(node_key, node_key),
                "planned_time": sample.planned_time,
                "start_date": start,
                "end_date": end,
                "members": people,
            })

        items.append({
            "requirement_id": req.id,
            "requirement_title": req.title,
            "priority": req.priority,
            "status": req.status,
            "status_label": NODE_LABEL.get(req.status, req.status),
            "nodes": nodes_data,
        })

    return success({
        "requirements": items,
        "date_range": {"start": global_min_date, "end": global_max_date} if global_min_date else None,
    })
