import random
import string

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success, fail
from app.models.hr_model import Employee, Team, EmployeeSkill, Schedule, LeaveRecord
from app.models.user_model import User
from app.security.password_hasher import hash_password
from app.util.time_utils import now_str

router = APIRouter(prefix="/hr", tags=["HR Management"])

_ALL_EMP_FIELDS = (
    "name", "email", "phone", "position", "department",
    "team_id", "status", "role", "level", "hire_date",
    "sync_source", "sync_id",
)


# ---- Employee ----
@router.get("/employees")
async def list_employees(team_id: int = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(Employee).order_by(Employee.id.desc())
    if team_id:
        stmt = stmt.where(Employee.team_id == team_id)
    result = await db.execute(stmt)
    return success([{
        "id": e.id, "user_id": e.user_id, "name": e.name,
        "email": e.email, "phone": e.phone,
        "position": e.position, "department": e.department,
        "team_id": e.team_id, "status": e.status,
        "role": e.role, "level": e.level, "hire_date": e.hire_date,
        "sync_source": e.sync_source, "sync_id": e.sync_id,
        "can_login": e.user_id is not None,
    } for e in result.scalars().all()])


@router.post("/employees")
async def create_employee(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    emp = Employee(
        user_id=body.get("user_id"), name=body.get("name", ""),
        email=body.get("email"), phone=body.get("phone"),
        position=body.get("position"), department=body.get("department"),
        team_id=body.get("team_id"), status=body.get("status", "active"),
        role=body.get("role", "developer"), level=body.get("level", "member"),
        hire_date=body.get("hire_date"),
        sync_source=body.get("sync_source"), sync_id=body.get("sync_id"),
        created_at=ts, updated_at=ts,
    )
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return success({"id": emp.id, "name": emp.name})


@router.put("/employees/{emp_id}")
async def update_employee(emp_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    emp = await db.get(Employee, emp_id)
    if not emp:
        return fail("员工不存在")
    for field in _ALL_EMP_FIELDS:
        if field in body:
            setattr(emp, field, body[field])
    emp.updated_at = now_str()
    await db.commit()
    return success({"id": emp.id})


# ---- Sync: mock fetch from external platforms ----
_MOCK_PLATFORMS = {
    "feishu": {
        "name": "飞书",
        "users": [
            {"name": "王明", "email": "wangming@feishu.cn", "phone": "13800001001", "department": "工程部", "position": "高级开发工程师", "role": "developer"},
            {"name": "李娜", "email": "lina@feishu.cn", "phone": "13800001002", "department": "产品部", "position": "产品经理", "role": "product"},
            {"name": "张伟", "email": "zhangwei@feishu.cn", "phone": "13800001003", "department": "测试部", "position": "测试工程师", "role": "tester"},
            {"name": "赵丽", "email": "zhaoli@feishu.cn", "phone": "13800001004", "department": "工程部", "position": "前端开发", "role": "developer"},
            {"name": "陈强", "email": "chenqiang@feishu.cn", "phone": "13800001005", "department": "工程部", "position": "后端开发", "role": "developer"},
        ],
    },
    "dingtalk": {
        "name": "钉钉",
        "users": [
            {"name": "刘洋", "email": "liuyang@dingtalk.com", "phone": "13900002001", "department": "工程部", "position": "架构师", "role": "developer"},
            {"name": "周芳", "email": "zhoufang@dingtalk.com", "phone": "13900002002", "department": "测试部", "position": "测试主管", "role": "tester"},
            {"name": "吴鹏", "email": "wupeng@dingtalk.com", "phone": "13900002003", "department": "产品部", "position": "产品总监", "role": "product"},
            {"name": "孙婷", "email": "sunting@dingtalk.com", "phone": "13900002004", "department": "设计部", "position": "UI设计师", "role": "product"},
        ],
    },
    "wecom": {
        "name": "企业微信",
        "users": [
            {"name": "黄磊", "email": "huanglei@wecom.work", "phone": "13700003001", "department": "运维部", "position": "运维工程师", "role": "developer"},
            {"name": "杨帆", "email": "yangfan@wecom.work", "phone": "13700003002", "department": "工程部", "position": "全栈工程师", "role": "developer"},
            {"name": "徐静", "email": "xujing@wecom.work", "phone": "13700003003", "department": "测试部", "position": "自动化测试", "role": "tester"},
        ],
    },
}


@router.get("/sync/platforms")
async def list_sync_platforms():
    return success([
        {"key": k, "name": v["name"], "user_count": len(v["users"])}
        for k, v in _MOCK_PLATFORMS.items()
    ])


@router.post("/sync/fetch")
async def fetch_platform_users(body: dict, db: AsyncSession = Depends(get_db)):
    platform = body.get("platform", "")
    if platform not in _MOCK_PLATFORMS:
        return fail(f"不支持的平台: {platform}")

    result = await db.execute(select(Employee.email).where(Employee.email.isnot(None)))
    existing_emails = {row[0] for row in result.all()}

    platform_data = _MOCK_PLATFORMS[platform]
    users = []
    for u in platform_data["users"]:
        ext_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        users.append({
            **u,
            "sync_id": ext_id,
            "platform": platform,
            "platform_name": platform_data["name"],
            "already_exists": u["email"] in existing_emails,
        })
    return success({"platform": platform, "platform_name": platform_data["name"], "users": users})


@router.post("/sync/import")
async def import_platform_users(body: dict, db: AsyncSession = Depends(get_db)):
    users = body.get("users", [])
    platform = body.get("platform", "")
    if not users:
        return fail("没有可导入的人员")

    incoming_emails = [u.get("email") for u in users if u.get("email")]
    result = await db.execute(
        select(Employee.email).where(Employee.email.in_(incoming_emails))
    )
    existing_emails = {row[0] for row in result.all()}

    ts = now_str()
    imported = []
    skipped = []
    for u in users:
        if u.get("email") in existing_emails:
            skipped.append(u.get("name", ""))
            continue
        emp = Employee(
            name=u.get("name", ""), email=u.get("email"),
            phone=u.get("phone"), position=u.get("position"),
            department=u.get("department"),
            role=u.get("role", "developer"), level="member",
            sync_source=platform, sync_id=u.get("sync_id"),
            status="active", created_at=ts, updated_at=ts,
        )
        db.add(emp)
        imported.append(u.get("name", ""))
    await db.commit()
    return success({"imported": len(imported), "skipped": len(skipped),
                     "imported_names": imported, "skipped_names": skipped})


@router.post("/sync/enable-login/{emp_id}")
async def enable_employee_login(emp_id: int, db: AsyncSession = Depends(get_db)):
    emp = await db.get(Employee, emp_id)
    if not emp:
        return fail("员工不存在")
    if emp.user_id:
        return success({"message": "该员工已有登录账号", "user_id": emp.user_id})

    username = emp.email or emp.name
    existing_user = await db.execute(select(User).where(User.username == username))
    user = existing_user.scalar_one_or_none()

    ts = now_str()
    if not user:
        user = User(
            username=username,
            password=hash_password("123456"),
            is_active=emp.status == "active",
            created_at=ts, updated_at=ts,
        )
        db.add(user)
        await db.flush()

    emp.user_id = user.id
    emp.updated_at = ts
    await db.commit()
    return success({"user_id": user.id, "username": username, "default_password": "123456"})


@router.post("/sync/disable-login/{emp_id}")
async def disable_employee_login(emp_id: int, db: AsyncSession = Depends(get_db)):
    emp = await db.get(Employee, emp_id)
    if not emp:
        return fail("员工不存在")
    if not emp.user_id:
        return success({"message": "该员工无登录账号"})
    user = await db.get(User, emp.user_id)
    if user:
        user.is_active = False
        user.updated_at = now_str()
    emp.user_id = None
    emp.updated_at = now_str()
    await db.commit()
    return success({"message": "已禁用登录"})


@router.delete("/employees/{emp_id}")
async def delete_employee(emp_id: int, db: AsyncSession = Depends(get_db)):
    emp = await db.get(Employee, emp_id)
    if not emp:
        return fail("员工不存在")
    await db.delete(emp)
    await db.commit()
    return success(None)


# ---- Team ----
@router.get("/teams")
async def list_teams(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).order_by(Team.id.desc()))
    return success([{
        "id": t.id, "name": t.name, "description": t.description, "leader_id": t.leader_id,
    } for t in result.scalars().all()])


@router.post("/teams")
async def create_team(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    team = Team(
        name=body.get("name", ""), description=body.get("description"),
        leader_id=body.get("leader_id"), created_at=ts, updated_at=ts,
    )
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return success({"id": team.id, "name": team.name})


# ---- Schedule / Calendar ----
@router.get("/schedules")
async def list_schedules(
    employee_id: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Schedule).order_by(Schedule.schedule_date)
    if employee_id:
        stmt = stmt.where(Schedule.employee_id == employee_id)
    if start_date:
        stmt = stmt.where(Schedule.schedule_date >= start_date)
    if end_date:
        stmt = stmt.where(Schedule.schedule_date <= end_date)
    result = await db.execute(stmt)
    return success([{
        "id": s.id, "employee_id": s.employee_id, "project_id": s.project_id,
        "title": s.title, "schedule_date": s.schedule_date,
        "start_time": s.start_time, "end_time": s.end_time,
        "hours": s.hours, "schedule_type": s.schedule_type,
        "description": s.description,
    } for s in result.scalars().all()])


@router.post("/schedules")
async def create_schedule(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    schedule = Schedule(
        employee_id=body.get("employee_id"), project_id=body.get("project_id"),
        title=body.get("title", ""), schedule_date=body.get("schedule_date", ""),
        start_time=body.get("start_time"), end_time=body.get("end_time"),
        hours=body.get("hours"), schedule_type=body.get("schedule_type", "work"),
        description=body.get("description"), created_at=ts, updated_at=ts,
    )
    db.add(schedule)
    await db.commit()
    return success({"id": schedule.id})


# ---- Schedule conflict check ----
@router.post("/schedules/conflicts")
async def check_schedule_conflicts(body: dict, db: AsyncSession = Depends(get_db)):
    """检查员工在指定日期范围内是否存在排期冲突"""
    employee_ids = body.get("employee_ids", [])
    start_date = body.get("start_date", "")
    end_date = body.get("end_date", "")
    if not employee_ids or not start_date or not end_date:
        return success({"conflicts": []})

    stmt = (
        select(Schedule)
        .where(
            Schedule.employee_id.in_(employee_ids),
            Schedule.schedule_date >= start_date,
            Schedule.schedule_date <= end_date,
        )
        .order_by(Schedule.schedule_date)
    )
    result = await db.execute(stmt)
    schedules = result.scalars().all()

    emp_stmt = select(Employee).where(Employee.id.in_(employee_ids))
    emp_result = await db.execute(emp_stmt)
    emp_map = {e.id: e.name for e in emp_result.scalars().all()}

    conflict_map: dict = {}
    for s in schedules:
        eid = s.employee_id
        if eid not in conflict_map:
            conflict_map[eid] = {
                "employee_id": eid,
                "employee_name": emp_map.get(eid, ""),
                "dates": [],
                "items": [],
            }
        conflict_map[eid]["dates"].append(s.schedule_date)
        conflict_map[eid]["items"].append({
            "id": s.id, "title": s.title, "date": s.schedule_date,
            "type": s.schedule_type, "project_id": s.project_id,
        })

    return success({"conflicts": list(conflict_map.values())})


@router.delete("/schedules/by-source")
async def delete_schedules_by_source(
    source_type: str = Query(...),
    source_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """按来源删除排期（如需求节点变更时清理旧排期）"""
    stmt = select(Schedule).where(
        Schedule.description.like(f"[{source_type}:{source_id}]%")
    )
    result = await db.execute(stmt)
    for s in result.scalars().all():
        await db.delete(s)
    await db.commit()
    return success(None)


@router.post("/schedules/batch")
async def batch_create_schedules(body: dict, db: AsyncSession = Depends(get_db)):
    """批量创建排期 - 支持日期范围和多人"""
    items = body.get("items", [])
    ts = now_str()
    created = 0
    for item in items:
        schedule = Schedule(
            employee_id=item.get("employee_id"),
            project_id=item.get("project_id"),
            title=item.get("title", ""),
            schedule_date=item.get("schedule_date", ""),
            start_time=item.get("start_time"),
            end_time=item.get("end_time"),
            hours=item.get("hours"),
            schedule_type=item.get("schedule_type", "work"),
            description=item.get("description", ""),
            created_at=ts, updated_at=ts,
        )
        db.add(schedule)
        created += 1
    await db.commit()
    return success({"created": created})


# ---- Leave ----
@router.get("/leaves")
async def list_leaves(employee_id: int = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(LeaveRecord).order_by(LeaveRecord.id.desc())
    if employee_id:
        stmt = stmt.where(LeaveRecord.employee_id == employee_id)
    result = await db.execute(stmt)
    return success([{
        "id": l.id, "employee_id": l.employee_id, "leave_type": l.leave_type,
        "start_date": l.start_date, "end_date": l.end_date,
        "status": l.status, "reason": l.reason,
    } for l in result.scalars().all()])


@router.post("/leaves")
async def create_leave(body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    leave = LeaveRecord(
        employee_id=body.get("employee_id"), leave_type=body.get("leave_type", "annual"),
        start_date=body.get("start_date", ""), end_date=body.get("end_date", ""),
        status="pending", reason=body.get("reason"), created_at=ts, updated_at=ts,
    )
    db.add(leave)
    await db.commit()
    return success({"id": leave.id})


# ---- Skills ----
@router.get("/employees/{emp_id}/skills")
async def list_employee_skills(emp_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmployeeSkill).where(EmployeeSkill.employee_id == emp_id)
    )
    return success([{
        "id": s.id, "skill_name": s.skill_name, "level": s.level,
    } for s in result.scalars().all()])


@router.post("/employees/{emp_id}/skills")
async def add_employee_skill(emp_id: int, body: dict, db: AsyncSession = Depends(get_db)):
    ts = now_str()
    skill = EmployeeSkill(
        employee_id=emp_id, skill_name=body.get("skill_name", ""),
        level=body.get("level", "intermediate"), created_at=ts, updated_at=ts,
    )
    db.add(skill)
    await db.commit()
    return success({"id": skill.id})
