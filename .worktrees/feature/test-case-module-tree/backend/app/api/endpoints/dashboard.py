import asyncio

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.response import success
from app.models.hr_model import Employee
from app.models.project_model import Project
from app.models.requirement_model import Requirement, RequirementNodeMember
from app.models.defect_model import Defect
from app.services import dashboard_service

router = APIRouter()

NODE_LABELS = {
    "requirement_review": "需求评审",
    "tech_review": "技术评审",
    "case_review": "用例评审",
    "testing": "测试执行",
    "acceptance": "验收测试",
    "released": "发布上线",
    "regression": "线上回归",
}

STATUS_LABELS = {
    "draft": "草稿", "approved": "已审批", "active": "进行中",
    "archived": "已归档", "suspended": "暂停",
}


@router.get("/dashboard")
async def get_dashboard_overview(request: Request, current_user: dict = Depends(get_current_user)):
    data = await dashboard_service.get_dashboard_overview()
    return success(data, request.state.tid)


@router.get("/dashboard/my-info")
async def get_my_employee_info(
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """根据 user_id 获取对应员工信息"""
    result = await db.execute(
        select(Employee).where(Employee.user_id == user_id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        return success(None)
    return success({
        "id": emp.id, "name": emp.name, "role": emp.role,
        "position": emp.position, "department": emp.department,
        "level": emp.level, "email": emp.email,
    })


@router.get("/dashboard/admin-view")
async def get_admin_dashboard(db: AsyncSession = Depends(get_db)):
    """超级管理员看板 - 查看所有项目/需求/缺陷/人员统计"""
    proj_result = await db.execute(select(Project).order_by(Project.id.desc()))
    projects = proj_result.scalars().all()
    req_result = await db.execute(select(Requirement))
    all_reqs = req_result.scalars().all()
    defect_result = await db.execute(select(Defect))
    all_defects = defect_result.scalars().all()
    emp_result = await db.execute(select(Employee).where(Employee.status == "active"))
    all_emps = emp_result.scalars().all()

    proj_map = {p.id: p for p in projects}
    req_by_proj: dict[int, list] = {}
    for r in all_reqs:
        if r.project_id:
            req_by_proj.setdefault(r.project_id, []).append(r)

    open_statuses = {"open", "in_progress", "reopen"}
    defect_by_proj: dict[int, int] = {}
    total_open = 0
    for d in all_defects:
        if d.status in open_statuses:
            total_open += 1
            if d.project_id:
                defect_by_proj[d.project_id] = defect_by_proj.get(d.project_id, 0) + 1

    role_counts = {"product": 0, "developer": 0, "tester": 0, "other": 0}
    for e in all_emps:
        bucket = role_counts.get(e.role or "", None)
        if bucket is not None:
            role_counts[e.role] += 1
        else:
            role_counts["other"] += 1

    project_list = []
    for p in projects:
        reqs = req_by_proj.get(p.id, [])
        status_dist: dict[str, int] = {}
        for r in reqs:
            status_dist[r.status] = status_dist.get(r.status, 0) + 1
        project_list.append({
            "project_id": p.id,
            "project_name": p.name,
            "project_status": p.status,
            "project_status_label": STATUS_LABELS.get(p.status, p.status),
            "requirement_count": len(reqs),
            "requirement_status_dist": {NODE_LABELS.get(k, k): v for k, v in status_dist.items()},
            "open_bugs": defect_by_proj.get(p.id, 0),
        })

    active_count = sum(1 for p in projects if p.status == "active")

    return success({
        "role": "admin",
        "role_label": "超级管理员",
        "employee_name": "管理员",
        "position": "超级管理员",
        "projects": project_list,
        "summary": {
            "total_projects": len(projects),
            "active_projects": active_count,
            "total_requirements": len(all_reqs),
            "open_bugs": total_open,
            "total_defects": len(all_defects),
            "total_employees": len(all_emps),
        },
        "team_overview": role_counts,
    })


@router.get("/dashboard/role-view")
async def get_role_dashboard(
    employee_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """角色看板 - 根据员工 ID 返回角色相关的项目/需求/缺陷数据"""
    emp = await db.get(Employee, employee_id)
    if not emp:
        return success({"role": "unknown", "projects": []})

    role = emp.role or "developer"

    role_mapping = {
        "product": ["product"],
        "developer": ["backend", "frontend"],
        "tester": ["tester"],
    }
    member_roles = role_mapping.get(role, [role])
    if emp.position and "前端" in emp.position:
        member_roles = ["frontend"]
    elif emp.position and ("后端" in emp.position or "架构" in emp.position or "全栈" in emp.position):
        member_roles = ["backend"]

    node_result = await db.execute(
        select(RequirementNodeMember).where(
            RequirementNodeMember.employee_id == employee_id
        )
    )
    node_members = node_result.scalars().all()

    req_ids = list({nm.requirement_id for nm in node_members})
    if not req_ids:
        return success({
            "role": role,
            "role_label": {"product": "产品", "developer": "开发", "tester": "测试"}.get(role, role),
            "employee_name": emp.name,
            "position": emp.position,
            "projects": [],
            "summary": {"total_projects": 0, "active_projects": 0, "total_requirements": 0, "open_bugs": 0},
        })

    req_result = await db.execute(
        select(Requirement).where(Requirement.id.in_(req_ids))
    )
    requirements = req_result.scalars().all()
    req_map = {r.id: r for r in requirements}

    project_ids = list({r.project_id for r in requirements if r.project_id})
    proj_result = await db.execute(
        select(Project).where(Project.id.in_(project_ids))
    ) if project_ids else None
    projects = proj_result.scalars().all() if proj_result else []
    proj_map = {p.id: p for p in projects}

    defect_counts = {}
    if project_ids:
        defect_result = await db.execute(
            select(Defect.project_id, func.count()).where(
                Defect.project_id.in_(project_ids),
                Defect.status.in_(["open", "in_progress", "reopen"]),
            ).group_by(Defect.project_id)
        )
        defect_counts = {pid: cnt for pid, cnt in defect_result.all()}

    nm_by_req: dict[int, list] = {}
    for nm in node_members:
        nm_by_req.setdefault(nm.requirement_id, []).append(nm)

    project_data: dict[int, dict] = {}
    for rid, req in req_map.items():
        pid = req.project_id
        if not pid or pid not in proj_map:
            continue
        proj = proj_map[pid]
        if pid not in project_data:
            project_data[pid] = {
                "project_id": pid,
                "project_name": proj.name,
                "project_status": proj.status,
                "project_status_label": STATUS_LABELS.get(proj.status, proj.status),
                "requirements": [],
                "open_bugs": defect_counts.get(pid, 0),
            }

        nodes_for_req = nm_by_req.get(rid, [])
        testing_time = None
        my_nodes = []
        for nm in nodes_for_req:
            my_nodes.append({
                "node": nm.node,
                "node_label": NODE_LABELS.get(nm.node, nm.node),
                "role": nm.role,
                "planned_time": nm.planned_time,
            })
            if nm.node == "testing" and nm.planned_time:
                testing_time = nm.planned_time

        project_data[pid]["requirements"].append({
            "id": req.id,
            "title": req.title,
            "status": req.status,
            "status_label": NODE_LABELS.get(req.status, req.status),
            "priority": req.priority,
            "testing_time": testing_time,
            "my_nodes": my_nodes,
        })

    project_list = sorted(project_data.values(), key=lambda x: x["project_status"] == "active", reverse=True)

    active_count = sum(1 for p in project_list if p["project_status"] == "active")
    total_open_bugs = sum(p["open_bugs"] for p in project_list)
    total_reqs = sum(len(p["requirements"]) for p in project_list)

    return success({
        "role": role,
        "role_label": {"product": "产品", "developer": "开发", "tester": "测试"}.get(role, role),
        "employee_name": emp.name,
        "position": emp.position,
        "projects": project_list,
        "summary": {
            "total_projects": len(project_list),
            "active_projects": active_count,
            "total_requirements": total_reqs,
            "open_bugs": total_open_bugs,
        },
    })
