import request from '../utils/request'

export async function testDBConnection(payload: {
  host: string
  port: number
  username: string
  password: string
  database?: string
  db_type?: string
}) {
  return request.post('/efficiency-tools/db/test-connect', payload)
}

export async function executeDBQuery(payload: {
  host: string
  port: number
  username: string
  password: string
  database: string
  db_type?: string
  sql: string
}) {
  return request.post('/efficiency-tools/db/query', payload)
}

export async function listDBTables(payload: {
  host: string
  port: number
  username: string
  password: string
  database: string
  db_type?: string
}) {
  return request.post('/efficiency-tools/db/tables', payload)
}

export async function getTableSchema(payload: {
  host: string
  port: number
  username: string
  password: string
  database: string
  db_type?: string
  sql: string
}) {
  return request.post('/efficiency-tools/db/table-schema', payload)
}

export async function pingServer(payload: {
  host: string
  port?: number
  connect_type?: string
}) {
  return request.post('/efficiency-tools/server/ping', payload)
}

export async function checkServerPort(payload: {
  host: string
  port: number
  connect_type?: string
}) {
  return request.post('/efficiency-tools/server/port-check', payload)
}

export async function batchPortCheck(payload: {
  host: string
  ports: number[]
}) {
  return request.post('/efficiency-tools/server/batch-port-check', payload)
}
