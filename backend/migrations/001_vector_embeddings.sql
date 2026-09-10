-- Run once against an existing database before deploying the vector models.
-- The transaction rolls back if old embeddings are not 384-dimensional.
BEGIN;
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE users ADD COLUMN IF NOT EXISTS embedding vector(384);
ALTER TABLE books ALTER COLUMN embedding TYPE vector(384)
    USING embedding::vector(384);
COMMIT;
