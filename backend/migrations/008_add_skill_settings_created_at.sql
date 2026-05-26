-- 检查条件: table=skill_settings column_missing=created_at
ALTER TABLE skill_settings ADD COLUMN created_at VARCHAR DEFAULT '';
