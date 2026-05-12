"""
模拟主流程数据种子脚本 — 使用同步 sqlite3, 幂等
运行: cd backend && python3 -m seed_data
"""
import sqlite3, os, sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "app.db")
_BJ = timezone(timedelta(hours=8))
ts = datetime.now(_BJ).strftime("%Y-%m-%d %H:%M:%S")


def main():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    # -- 确保新列存在 --
    cols = {r[1] for r in c.execute("PRAGMA table_info(requirements)").fetchall()}
    for col in ("product_owner_id", "dev_owner_id", "test_owner_id"):
        if col not in cols:
            c.execute(f"ALTER TABLE requirements ADD COLUMN {col} INTEGER")
            print(f"  ➕ requirements 添加列 {col}")

    # -- 清理旧种子 --
    c.execute("DELETE FROM requirement_node_members")
    c.execute("DELETE FROM requirements")
    c.execute("DELETE FROM projects")
    c.execute("DELETE FROM employees")
    c.execute("DELETE FROM teams")
    conn.commit()
    print("🗑️  旧数据已清理")

    # -- 1. 团队 --
    c.execute("INSERT INTO teams (name, description, created_at, updated_at) VALUES (?,?,?,?)",
              ("核心研发组", "产品研发核心团队", ts, ts))
    team_id = c.lastrowid
    print(f"✅ 团队: 核心研发组 (id={team_id})")

    # -- 2. 员工 --
    employees = [
        ("张三", "zhangsan@test.com", "产品经理", "product", "leader"),
        ("李四", "lisi@test.com", "后端工程师", "developer", "member"),
        ("王五", "wangwu@test.com", "前端工程师", "developer", "member"),
        ("赵六", "zhaoliu@test.com", "测试工程师", "tester", "member"),
        ("钱七", "qianqi@test.com", "测试组长", "tester", "leader"),
        ("孙八", "sunba@test.com", "后端架构师", "developer", "leader"),
        ("周九", "zhoujiu@test.com", "产品助理", "product", "member"),
    ]
    emp_ids = []
    for name, email, pos, role, level in employees:
        c.execute("""INSERT INTO employees (name, email, position, role, level, department, team_id, status, hire_date, created_at, updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (name, email, pos, role, level, "研发部", team_id, "active", "2024-01-15", ts, ts))
        emp_ids.append(c.lastrowid)
        print(f"  👤 {name} ({pos}, {role}) id={c.lastrowid}")

    # -- 3. 项目 --
    projects = [
        ("电商平台 v2.0", "电商平台全面升级，新支付系统、推荐引擎、用户中心改版", "approved"),
        ("内部管理系统", "OA审批、人力资源、财务报销一体化系统", "approved"),
        ("移动端 App 重构", "Flutter 技术栈重构 iOS/Android 双端应用", "draft"),
    ]
    proj_ids = []
    for name, desc, status in projects:
        c.execute("INSERT INTO projects (name, description, status, created_at, updated_at) VALUES (?,?,?,?,?)",
                  (name, desc, status, ts, ts))
        proj_ids.append(c.lastrowid)
        print(f"  📁 {name} (status={status}) id={c.lastrowid}")

    # -- 4. 需求 --
    reqs = [
        ("用户登录功能优化", "支持手机验证码登录、第三方OAuth登录", proj_ids[0], "high", "tech_review", emp_ids[0], emp_ids[1], emp_ids[3]),
        ("商品推荐算法升级", "基于协同过滤+深度学习的个性化推荐", proj_ids[0], "critical", "requirement_review", emp_ids[0], emp_ids[5], emp_ids[4]),
        ("支付系统对接微信支付", "接入微信支付SDK，支持JSAPI/Native/H5/小程序支付", proj_ids[0], "high", "testing", emp_ids[6], emp_ids[1], emp_ids[3]),
        ("OA审批流引擎设计", "自定义审批流程、多级审批、条件分支、会签", proj_ids[1], "high", "case_review", emp_ids[0], emp_ids[5], emp_ids[4]),
        ("员工考勤统计模块", "打卡记录、加班申请、请假审批、月度统计报表", proj_ids[1], "medium", "requirement_review", emp_ids[6], emp_ids[2], emp_ids[3]),
        ("财务报销电子化", "拍照上传发票、OCR识别、审批流程、对接财务系统", proj_ids[1], "medium", "acceptance", emp_ids[0], emp_ids[1], emp_ids[4]),
    ]
    req_ids = []
    for title, desc, pid, pri, st, po, dev, test in reqs:
        c.execute("""INSERT INTO requirements (title, description, project_id, priority, status, req_type, product_owner_id, dev_owner_id, test_owner_id, created_at, updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (title, desc, pid, pri, st, "functional", po, dev, test, ts, ts))
        req_ids.append(c.lastrowid)
        print(f"  📝 {title} (status={st}) id={c.lastrowid}")

    # -- 5. 节点人员 --
    nodes = ["requirement_review", "tech_review", "case_review", "testing", "acceptance", "released", "regression"]
    roles_map = {"product": [0], "backend": [1], "frontend": [2], "tester": [3], "poc": [5]}
    for rid in req_ids[:2]:
        for node in nodes:
            for role, idxs in roles_map.items():
                for idx in idxs:
                    c.execute("""INSERT INTO requirement_node_members (requirement_id, node, role, employee_id, planned_time, created_at, updated_at)
                                 VALUES (?,?,?,?,?,?,?)""",
                              (rid, node, role, emp_ids[idx], "2025-06-01 ~ 2025-06-30", ts, ts))
    print(f"  🔗 前 2 条需求已绑定全部节点人员")

    # -- 6. 人力排期 (Schedule) --
    schedule_data = [
        (emp_ids[0], proj_ids[0], "电商v2需求评审", "2025-06-02", "09:00", "12:00", "3", "work"),
        (emp_ids[1], proj_ids[0], "登录模块后端开发", "2025-06-03", "09:00", "18:00", "8", "work"),
        (emp_ids[2], proj_ids[0], "登录页面前端开发", "2025-06-03", "09:00", "18:00", "8", "work"),
        (emp_ids[3], proj_ids[0], "登录模块测试用例编写", "2025-06-05", "09:00", "18:00", "8", "work"),
        (emp_ids[5], proj_ids[1], "OA审批架构设计", "2025-06-04", "14:00", "18:00", "4", "work"),
        (emp_ids[4], proj_ids[1], "OA审批测试策略", "2025-06-06", "09:00", "12:00", "3", "work"),
        (emp_ids[1], proj_ids[0], "微信支付接口联调", "2025-06-10", "09:00", "18:00", "8", "work"),
        (emp_ids[6], proj_ids[1], "考勤模块需求梳理", "2025-06-07", "09:00", "17:00", "7", "work"),
    ]
    for eid, pid, title, sdate, start, end, hours, stype in schedule_data:
        c.execute("""INSERT INTO schedules (employee_id, project_id, title, schedule_date, start_time, end_time, hours, schedule_type, created_at, updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (eid, pid, title, sdate, start, end, hours, stype, ts, ts))
    print(f"  📅 排期: {len(schedule_data)} 条")

    conn.commit()
    conn.close()
    print(f"\n🎉 种子数据完成!")
    print(f"   团队: 1 / 员工: {len(emp_ids)} / 项目: {len(proj_ids)} / 需求: {len(req_ids)} / 排期: {len(schedule_data)}")


if __name__ == "__main__":
    main()
