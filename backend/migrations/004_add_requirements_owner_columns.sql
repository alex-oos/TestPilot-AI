-- 检查条件: table=requirements column_missing=product_owner_id
ALTER TABLE requirements ADD COLUMN product_owner_id INTEGER;
-- 检查条件: table=requirements column_missing=dev_owner_id
ALTER TABLE requirements ADD COLUMN dev_owner_id INTEGER;
-- 检查条件: table=requirements column_missing=test_owner_id
ALTER TABLE requirements ADD COLUMN test_owner_id INTEGER;
