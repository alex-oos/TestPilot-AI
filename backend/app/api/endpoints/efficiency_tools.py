import asyncio
import socket
from typing import Optional, List

from fastapi import APIRouter, Request
from loguru import logger
from pydantic import BaseModel

from app.ai.llm import llm_client
from app.core.response import success, fail

router = APIRouter(prefix="/efficiency-tools", tags=["Efficiency Tools"])

# ---------------------------------------------------------------------------
#  Pydantic models
# ---------------------------------------------------------------------------

class DBConnectRequest(BaseModel):
    host: str
    port: int = 3306
    username: str
    password: str
    database: Optional[str] = None
    db_type: str = "mysql"


class DBQueryRequest(BaseModel):
    host: str
    port: int = 3306
    username: str
    password: str
    database: str
    db_type: str = "mysql"
    sql: str


class AIQueryRequest(BaseModel):
    host: str
    port: int = 3306
    username: str
    password: str
    database: str
    db_type: str = "mysql"
    prompt: str


class ServerConnectRequest(BaseModel):
    host: str
    port: int = 22
    connect_type: str = "ping"


class SSHCommandRequest(BaseModel):
    host: str
    port: int = 22
    username: str
    password: Optional[str] = None
    private_key: Optional[str] = None
    command: str


class AIServerRequest(BaseModel):
    host: str
    port: int = 22
    username: str
    password: Optional[str] = None
    private_key: Optional[str] = None
    prompt: str


# ---------------------------------------------------------------------------
#  Database helpers
# ---------------------------------------------------------------------------

def _connect_mysql(cfg: DBConnectRequest):
    import pymysql
    return pymysql.connect(
        host=cfg.host, port=cfg.port, user=cfg.username,
        password=cfg.password, database=cfg.database or None,
        connect_timeout=5, charset="utf8mb4",
    )


def _connect_postgresql(cfg: DBConnectRequest):
    import psycopg2
    return psycopg2.connect(
        host=cfg.host, port=cfg.port, user=cfg.username,
        password=cfg.password, dbname=cfg.database or "postgres",
        connect_timeout=5,
    )


def _get_connection(cfg: DBConnectRequest):
    if cfg.db_type == "postgresql":
        return _connect_postgresql(cfg)
    return _connect_mysql(cfg)


def _show_databases_sql(db_type: str) -> str:
    if db_type == "postgresql":
        return "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
    return "SHOW DATABASES"


def _show_tables_sql(db_type: str) -> str:
    if db_type == "postgresql":
        return "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    return "SHOW TABLES"


def _describe_table_sql(db_type: str, table: str) -> str:
    if db_type == "postgresql":
        return (
            f"SELECT column_name, data_type, is_nullable, column_default "
            f"FROM information_schema.columns "
            f"WHERE table_schema = 'public' AND table_name = '{table}' "
            f"ORDER BY ordinal_position"
        )
    return f"DESCRIBE `{table}`"


BLOCKED_KEYWORDS = {"insert", "update", "delete", "drop", "alter", "create", "truncate", "grant", "revoke"}


def _is_readonly(sql: str) -> bool:
    first_word = sql.strip().split()[0].lower() if sql.strip() else ""
    return first_word not in BLOCKED_KEYWORDS


# ---------------------------------------------------------------------------
#  Database endpoints
# ---------------------------------------------------------------------------

@router.post("/db/test-connect")
async def test_db_connection(body: DBConnectRequest, request: Request):
    try:
        conn = await asyncio.to_thread(_get_connection, body)
        cursor = conn.cursor()
        if body.db_type == "postgresql":
            cursor.execute("SELECT version()")
        else:
            cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]

        databases: list[str] = []
        if not body.database:
            cursor.execute(_show_databases_sql(body.db_type))
            databases = [row[0] for row in cursor.fetchall()]

        cursor.close()
        conn.close()
        return success({"connected": True, "version": version, "databases": databases}, request.state.tid)
    except Exception as e:
        return fail(f"连接失败: {str(e)}", tid=request.state.tid)


@router.post("/db/tables")
async def list_db_tables(body: DBConnectRequest, request: Request):
    if not body.database:
        return fail("请指定数据库名称", tid=request.state.tid)
    try:
        conn = await asyncio.to_thread(_get_connection, body)
        cursor = conn.cursor()
        cursor.execute(_show_tables_sql(body.db_type))
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return success({"tables": tables}, request.state.tid)
    except Exception as e:
        return fail(f"获取表列表失败: {str(e)}", tid=request.state.tid)


@router.post("/db/table-schema")
async def get_table_schema(body: DBQueryRequest, request: Request):
    table_name = body.sql.strip()
    try:
        cfg = DBConnectRequest(**{k: getattr(body, k) for k in DBConnectRequest.model_fields})
        conn = await asyncio.to_thread(_get_connection, cfg)
        cursor = conn.cursor()
        cursor.execute(_describe_table_sql(body.db_type, table_name))
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return success({"columns": columns, "rows": [list(r) for r in rows]}, request.state.tid)
    except Exception as e:
        return fail(f"获取表结构失败: {str(e)}", tid=request.state.tid)


@router.post("/db/query")
async def execute_db_query(body: DBQueryRequest, request: Request):
    sql = body.sql.strip()
    if not _is_readonly(sql):
        return fail("安全限制：仅允许 SELECT / SHOW / DESCRIBE / EXPLAIN 语句", tid=request.state.tid)
    try:
        cfg = DBConnectRequest(**{k: getattr(body, k) for k in DBConnectRequest.model_fields})
        conn = await asyncio.to_thread(_get_connection, cfg)
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(500)
        total = cursor.rowcount
        cursor.close()
        conn.close()
        return success({
            "columns": columns,
            "rows": [list(r) for r in rows],
            "total": total,
            "truncated": total > 500,
        }, request.state.tid)
    except Exception as e:
        return fail(f"查询失败: {str(e)}", tid=request.state.tid)


# ---------------------------------------------------------------------------
#  AI natural-language → SQL
# ---------------------------------------------------------------------------

@router.post("/db/ai-query")
async def ai_query(body: AIQueryRequest, request: Request):
    """用自然语言描述需求，AI 生成 SQL 并执行"""
    try:
        cfg = DBConnectRequest(**{k: getattr(body, k) for k in DBConnectRequest.model_fields})
        conn = await asyncio.to_thread(_get_connection, cfg)
        cursor = conn.cursor()
        cursor.execute(_show_tables_sql(body.db_type))
        tables = [row[0] for row in cursor.fetchall()]

        schema_parts: list[str] = []
        for t in tables[:30]:
            try:
                cursor.execute(_describe_table_sql(body.db_type, t))
                cols = cursor.fetchall()
                col_descs = ", ".join(f"{c[0]} {c[1]}" for c in cols)
                schema_parts.append(f"  {t}({col_descs})")
            except Exception:
                schema_parts.append(f"  {t}(...)")
        cursor.close()
        conn.close()

        schema_text = "\n".join(schema_parts) if schema_parts else "(no tables)"
        db_type_label = "PostgreSQL" if body.db_type == "postgresql" else "MySQL"

        messages = [
            {
                "role": "system",
                "content": (
                    f"你是一个 {db_type_label} 数据库专家。用户会用自然语言描述他想查询的数据，"
                    f"你需要根据以下数据库 schema 生成一条合法的只读 SQL 查询语句。\n\n"
                    f"数据库: {body.database}\n"
                    f"表结构:\n{schema_text}\n\n"
                    f"要求:\n"
                    f"1. 只生成 SELECT 语句，不能有任何修改数据的操作\n"
                    f"2. 如果数据量可能很大，请加 LIMIT 100\n"
                    f"3. 只输出 SQL 语句本身，不要加任何解释或 markdown 格式\n"
                    f"4. SQL 语句不要包含分号"
                ),
            },
            {"role": "user", "content": body.prompt},
        ]

        generated_sql = await llm_client.chat(messages, temperature=0.1, max_tokens=500)
        generated_sql = generated_sql.strip().strip("`").strip()
        if generated_sql.lower().startswith("sql"):
            generated_sql = generated_sql[3:].strip()
        if generated_sql.endswith(";"):
            generated_sql = generated_sql[:-1].strip()

        if not _is_readonly(generated_sql):
            return success({
                "generated_sql": generated_sql,
                "executed": False,
                "error": "AI 生成的 SQL 包含写操作，已被拦截",
            }, request.state.tid)

        conn2 = await asyncio.to_thread(_get_connection, cfg)
        cursor2 = conn2.cursor()
        cursor2.execute(generated_sql)
        columns = [desc[0] for desc in cursor2.description] if cursor2.description else []
        rows = cursor2.fetchmany(500)
        total = cursor2.rowcount
        cursor2.close()
        conn2.close()

        return success({
            "generated_sql": generated_sql,
            "executed": True,
            "columns": columns,
            "rows": [list(r) for r in rows],
            "total": total,
            "truncated": total > 500,
        }, request.state.tid)

    except Exception as e:
        logger.error(f"AI query error: {e}")
        return fail(f"AI 查询失败: {str(e)}", tid=request.state.tid)


# ---------------------------------------------------------------------------
#  Server: Ping / Port check
# ---------------------------------------------------------------------------

@router.post("/server/ping")
async def ping_server(body: ServerConnectRequest, request: Request):
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "4", "-W", "3", body.host,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        output = stdout.decode("utf-8", errors="replace")
        return success({"reachable": proc.returncode == 0, "output": output}, request.state.tid)
    except asyncio.TimeoutError:
        return fail("Ping 超时", tid=request.state.tid)
    except Exception as e:
        return fail(f"Ping 失败: {str(e)}", tid=request.state.tid)


@router.post("/server/port-check")
async def check_server_port(body: ServerConnectRequest, request: Request):
    def _check():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            return sock.connect_ex((body.host, body.port)) == 0
        finally:
            sock.close()

    try:
        is_open = await asyncio.to_thread(_check)
        return success({"host": body.host, "port": body.port, "is_open": is_open}, request.state.tid)
    except Exception as e:
        return fail(f"端口检测失败: {str(e)}", tid=request.state.tid)


@router.post("/server/batch-port-check")
async def batch_port_check(request: Request):
    body = await request.json()
    host = body.get("host", "")
    port_list = body.get("ports", [])
    if not host or not port_list:
        return fail("请提供主机和端口列表", tid=request.state.tid)

    def _check_port(h: str, p: int):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        try:
            return {"port": p, "is_open": sock.connect_ex((h, p)) == 0}
        except Exception:
            return {"port": p, "is_open": False}
        finally:
            sock.close()

    tasks = [asyncio.to_thread(_check_port, host, int(p)) for p in port_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    port_results = [r for r in results if not isinstance(r, Exception)]
    return success({"host": host, "results": port_results}, request.state.tid)


# ---------------------------------------------------------------------------
#  Server: SSH command execution
# ---------------------------------------------------------------------------

def _ssh_exec(cfg: SSHCommandRequest) -> dict:
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs: dict = {"hostname": cfg.host, "port": cfg.port, "username": cfg.username, "timeout": 10}
    if cfg.private_key:
        import io
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(cfg.private_key))
        connect_kwargs["pkey"] = pkey
    else:
        connect_kwargs["password"] = cfg.password or ""
    client.connect(**connect_kwargs)
    _, stdout, stderr = client.exec_command(cfg.command, timeout=30)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    exit_code = stdout.channel.recv_exit_status()
    client.close()
    return {"stdout": out, "stderr": err, "exit_code": exit_code}


@router.post("/server/ssh-exec")
async def ssh_execute(body: SSHCommandRequest, request: Request):
    try:
        result = await asyncio.to_thread(_ssh_exec, body)
        return success(result, request.state.tid)
    except Exception as e:
        return fail(f"SSH 执行失败: {str(e)}", tid=request.state.tid)


@router.post("/server/ssh-test")
async def ssh_test_connection(body: SSHCommandRequest, request: Request):
    """测试 SSH 连接"""
    try:
        test_cmd = SSHCommandRequest(
            host=body.host, port=body.port, username=body.username,
            password=body.password, private_key=body.private_key,
            command="uname -a",
        )
        result = await asyncio.to_thread(_ssh_exec, test_cmd)
        return success({
            "connected": result["exit_code"] == 0,
            "system_info": result["stdout"].strip(),
        }, request.state.tid)
    except Exception as e:
        return fail(f"SSH 连接失败: {str(e)}", tid=request.state.tid)


# ---------------------------------------------------------------------------
#  AI natural-language → Linux command
# ---------------------------------------------------------------------------

@router.post("/server/ai-command")
async def ai_server_command(body: AIServerRequest, request: Request):
    """用自然语言描述需求，AI 生成 Linux 命令并通过 SSH 执行"""
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个 Linux 运维专家。用户会用自然语言描述他想在服务器上执行的操作，"
                    "你需要生成合法的 Linux 命令。\n\n"
                    "要求:\n"
                    "1. 只生成只读/查看类的命令（如 cat, tail, grep, ls, df, top -bn1, free, ps 等）\n"
                    "2. 绝对不能生成 rm, mkfs, dd, shutdown, reboot, kill -9, chmod 777 等危险命令\n"
                    "3. 如果查看日志，默认用 tail -n 100\n"
                    "4. 只输出命令本身，不要加任何解释或 markdown 格式\n"
                    "5. 如果需要管道组合多个命令可以用 | 连接"
                ),
            },
            {"role": "user", "content": body.prompt},
        ]

        generated_cmd = await llm_client.chat(messages, temperature=0.1, max_tokens=300)
        generated_cmd = generated_cmd.strip().strip("`").strip()
        if generated_cmd.lower().startswith("bash") or generated_cmd.lower().startswith("shell"):
            generated_cmd = generated_cmd.split("\n", 1)[-1].strip()

        dangerous = ["rm ", "rm\t", "rmdir", "mkfs", "dd ", "shutdown", "reboot",
                      "kill -9", "chmod 777", "chown", "> /dev/", ":(){ ", "fork"]
        for d in dangerous:
            if d in generated_cmd.lower():
                return success({
                    "generated_command": generated_cmd,
                    "executed": False,
                    "error": f"AI 生成的命令包含危险操作 ({d.strip()})，已被拦截",
                }, request.state.tid)

        ssh_cfg = SSHCommandRequest(
            host=body.host, port=body.port, username=body.username,
            password=body.password, private_key=body.private_key,
            command=generated_cmd,
        )
        result = await asyncio.to_thread(_ssh_exec, ssh_cfg)

        return success({
            "generated_command": generated_cmd,
            "executed": True,
            **result,
        }, request.state.tid)

    except Exception as e:
        logger.error(f"AI server command error: {e}")
        return fail(f"AI 命令执行失败: {str(e)}", tid=request.state.tid)
