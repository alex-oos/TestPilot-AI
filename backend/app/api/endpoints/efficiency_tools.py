import asyncio
import subprocess
import socket
from typing import Optional

import pymysql
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.response import success, fail

router = APIRouter(prefix="/efficiency-tools", tags=["Efficiency Tools"])


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


class ServerConnectRequest(BaseModel):
    host: str
    port: int = 22
    connect_type: str = "ping"


def _mysql_connect(cfg: DBConnectRequest):
    conn = pymysql.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.username,
        password=cfg.password,
        database=cfg.database or None,
        connect_timeout=5,
        charset="utf8mb4",
    )
    return conn


@router.post("/db/test-connect")
async def test_db_connection(body: DBConnectRequest, request: Request):
    """测试数据库连接"""
    try:
        conn = await asyncio.to_thread(_mysql_connect, body)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]

        databases = []
        if not body.database:
            cursor.execute("SHOW DATABASES")
            databases = [row[0] for row in cursor.fetchall()]

        cursor.close()
        conn.close()
        return success({
            "connected": True,
            "version": version,
            "databases": databases,
        }, request.state.tid)
    except Exception as e:
        return fail(f"连接失败: {str(e)}", tid=request.state.tid)


@router.post("/db/query")
async def execute_db_query(body: DBQueryRequest, request: Request):
    """执行 SQL 查询（只读模式，限制返回行数）"""
    sql = body.sql.strip()

    blocked = ["insert", "update", "delete", "drop", "alter", "create", "truncate", "grant", "revoke"]
    first_word = sql.split()[0].lower() if sql else ""
    if first_word in blocked:
        return fail("安全限制：仅允许 SELECT / SHOW / DESCRIBE / EXPLAIN 语句", tid=request.state.tid)

    try:
        cfg = DBConnectRequest(
            host=body.host,
            port=body.port,
            username=body.username,
            password=body.password,
            database=body.database,
            db_type=body.db_type,
        )
        conn = await asyncio.to_thread(_mysql_connect, cfg)
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(200)
        total = cursor.rowcount
        cursor.close()
        conn.close()

        return success({
            "columns": columns,
            "rows": [list(row) for row in rows],
            "total": total,
            "truncated": total > 200,
        }, request.state.tid)
    except Exception as e:
        return fail(f"查询失败: {str(e)}", tid=request.state.tid)


@router.post("/db/tables")
async def list_db_tables(body: DBConnectRequest, request: Request):
    """获取数据库中的表列表"""
    if not body.database:
        return fail("请指定数据库名称", tid=request.state.tid)
    try:
        conn = await asyncio.to_thread(_mysql_connect, body)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return success({"tables": tables}, request.state.tid)
    except Exception as e:
        return fail(f"获取表列表失败: {str(e)}", tid=request.state.tid)


@router.post("/db/table-schema")
async def get_table_schema(body: DBQueryRequest, request: Request):
    """获取表结构"""
    table_name = body.sql.strip()
    try:
        cfg = DBConnectRequest(
            host=body.host,
            port=body.port,
            username=body.username,
            password=body.password,
            database=body.database,
            db_type=body.db_type,
        )
        conn = await asyncio.to_thread(_mysql_connect, cfg)
        cursor = conn.cursor()
        cursor.execute(f"DESCRIBE `{table_name}`")
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return success({
            "columns": columns,
            "rows": [list(row) for row in rows],
        }, request.state.tid)
    except Exception as e:
        return fail(f"获取表结构失败: {str(e)}", tid=request.state.tid)


@router.post("/server/ping")
async def ping_server(body: ServerConnectRequest, request: Request):
    """Ping 测试服务器连通性"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "4", "-W", "3", body.host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        output = stdout.decode("utf-8", errors="replace")
        return success({
            "reachable": proc.returncode == 0,
            "output": output,
        }, request.state.tid)
    except asyncio.TimeoutError:
        return fail("Ping 超时", tid=request.state.tid)
    except Exception as e:
        return fail(f"Ping 失败: {str(e)}", tid=request.state.tid)


@router.post("/server/port-check")
async def check_server_port(body: ServerConnectRequest, request: Request):
    """检查服务器端口是否开放"""
    def _check():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            result = sock.connect_ex((body.host, body.port))
            return result == 0
        finally:
            sock.close()

    try:
        is_open = await asyncio.to_thread(_check)
        return success({
            "host": body.host,
            "port": body.port,
            "is_open": is_open,
        }, request.state.tid)
    except Exception as e:
        return fail(f"端口检测失败: {str(e)}", tid=request.state.tid)


@router.post("/server/batch-port-check")
async def batch_port_check(request: Request, host: str = "", ports: str = ""):
    """批量检查服务器端口"""
    import json
    body = await request.json()
    host = body.get("host", "")
    port_list = body.get("ports", [])

    if not host or not port_list:
        return fail("请提供主机和端口列表", tid=request.state.tid)

    def _check_port(h: str, p: int):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        try:
            result = sock.connect_ex((h, p))
            return {"port": p, "is_open": result == 0}
        except:
            return {"port": p, "is_open": False}
        finally:
            sock.close()

    tasks = [asyncio.to_thread(_check_port, host, int(p)) for p in port_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    port_results = []
    for r in results:
        if isinstance(r, Exception):
            continue
        port_results.append(r)

    return success({
        "host": host,
        "results": port_results,
    }, request.state.tid)
