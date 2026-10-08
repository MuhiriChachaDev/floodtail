-- Enable pgvector for RAG document chunks + long-term agent memory.
-- Tables are created lazily by packages.rag / packages.memory on first use.
CREATE EXTENSION IF NOT EXISTS vector;
