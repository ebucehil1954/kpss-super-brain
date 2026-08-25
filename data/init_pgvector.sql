-- KPSS Super-Brain: PostgreSQL + pgvector Şema Başlatıcı (init_pgvector.sql)

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    id SERIAL PRIMARY KEY,
    record_id VARCHAR(64) UNIQUE NOT NULL,
    lesson VARCHAR(64) NOT NULL,
    topic VARCHAR(128) NOT NULL,
    title VARCHAR(256),
    content TEXT NOT NULL,
    source_type VARCHAR(64) DEFAULT 'VIDEO',
    source_url TEXT,
    confidence_score FLOAT DEFAULT 0.90,
    embedding vector(384),
    provenance JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- HNSW Kosinüs Benzerliği İndeksi (all-MiniLM-L6-v2: 384 dimensions)
CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings_hnsw 
ON knowledge_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_knowledge_lesson_topic 
ON knowledge_embeddings (lesson, topic);
