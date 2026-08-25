-- 006: OZON 直发附件 — 增加 file_path 列（文件系统存储路径，替代数据库二进制）
-- 执行方式: psql -f migrations/006_direct_files_file_path.sql
ALTER TABLE ozon.ozon_direct_files
    ADD COLUMN IF NOT EXISTS file_path VARCHAR(500);
COMMENT ON COLUMN ozon.ozon_direct_files.file_path IS '文件系统存储路径（相对 direct_file_dir）';
