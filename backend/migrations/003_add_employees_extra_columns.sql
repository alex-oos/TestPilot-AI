-- 检查条件: table=employees column_missing=role
ALTER TABLE employees ADD COLUMN role VARCHAR;
-- 检查条件: table=employees column_missing=level
ALTER TABLE employees ADD COLUMN level VARCHAR;
-- 检查条件: table=employees column_missing=hire_date
ALTER TABLE employees ADD COLUMN hire_date VARCHAR;
-- 检查条件: table=employees column_missing=sync_source
ALTER TABLE employees ADD COLUMN sync_source VARCHAR;
-- 检查条件: table=employees column_missing=sync_id
ALTER TABLE employees ADD COLUMN sync_id VARCHAR;
