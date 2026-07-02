import request from '../utils/request'

// ---------- 数据库工具 ----------

export async function testDBConnection(payload: {
  host: string; port: number; username: string; password: string;
  database?: string; db_type?: string
}) {
  return request.post('/efficiency-tools/db/test-connect', payload)
}

export async function listDBTables(payload: {
  host: string; port: number; username: string; password: string;
  database: string; db_type?: string
}) {
  return request.post('/efficiency-tools/db/tables', payload)
}

export async function getTableSchema(payload: {
  host: string; port: number; username: string; password: string;
  database: string; db_type?: string; sql: string
}) {
  return request.post('/efficiency-tools/db/table-schema', payload)
}

export async function executeDBQuery(payload: {
  host: string; port: number; username: string; password: string;
  database: string; db_type?: string; sql: string
}) {
  return request.post('/efficiency-tools/db/query', payload)
}

export async function aiDBQuery(payload: {
  host: string; port: number; username: string; password: string;
  database: string; db_type?: string; prompt: string
}) {
  return request.post('/efficiency-tools/db/ai-query', payload)
}

// ---------- 服务器工具 ----------

export async function pingServer(payload: { host: string }) {
  return request.post('/efficiency-tools/server/ping', payload)
}

export async function checkServerPort(payload: { host: string; port: number }) {
  return request.post('/efficiency-tools/server/port-check', payload)
}

export async function batchPortCheck(payload: { host: string; ports: number[] }) {
  return request.post('/efficiency-tools/server/batch-port-check', payload)
}

export async function sshTestConnection(payload: {
  host: string; port: number; username: string;
  password?: string; private_key?: string; command?: string
}) {
  return request.post('/efficiency-tools/server/ssh-test', payload)
}

export async function sshExecute(payload: {
  host: string; port: number; username: string;
  password?: string; private_key?: string; command: string
}) {
  return request.post('/efficiency-tools/server/ssh-exec', payload)
}

export async function aiServerCommand(payload: {
  host: string; port: number; username: string;
  password?: string; private_key?: string; prompt: string
}) {
  return request.post('/efficiency-tools/server/ai-command', payload)
}
