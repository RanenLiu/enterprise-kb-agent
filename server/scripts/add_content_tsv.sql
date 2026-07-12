-- chunks 表全文检索 tsvector 支持
-- 用法: psql -U kbuser -d enterprise_kb -f add_content_tsv.sql

ALTER TABLE chunks ADD COLUMN IF NOT EXISTS content_tsv tsvector;

CREATE OR REPLACE FUNCTION chunks_content_tsv_update() RETURNS trigger AS $$
BEGIN
    NEW.content_tsv := to_tsvector('simple', COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_chunks_content_tsv ON chunks;
CREATE TRIGGER trg_chunks_content_tsv
    BEFORE INSERT OR UPDATE OF content
    ON chunks
    FOR EACH ROW
    EXECUTE FUNCTION chunks_content_tsv_update();

-- 为已有数据初始化
UPDATE chunks SET content = content WHERE content IS NOT NULL AND content_tsv IS NULL;
