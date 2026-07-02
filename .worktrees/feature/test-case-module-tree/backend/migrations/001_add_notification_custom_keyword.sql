-- 检查条件: table=notification_configs column_missing=custom_keyword
ALTER TABLE notification_configs ADD COLUMN custom_keyword VARCHAR DEFAULT '';
