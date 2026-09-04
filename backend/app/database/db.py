# app/db.py

import psycopg

from app.config import DATABASE_URL


def get_connection():
    return psycopg.connect(DATABASE_URL)

def test_connection():
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                cursor.execute("SELECT version();")
                version = cursor.fetchone()

                cursor.execute("""
                    SELECT extversion
                    FROM pg_extension
                    WHERE extname = 'vector';
                """)
                vector_version = cursor.fetchone()

                print("✅ PostgreSQL connection successful")
                print(f"PostgreSQL: {version[0]}")

                if vector_version:
                    print(
                        f"✅ pgvector installed: "
                        f"v{vector_version[0]}"
                    )
                else:
                    print("❌ pgvector extension not installed")

    except Exception as e:
        print("❌ PostgreSQL connection failed")
        print(f"Error: {e}")

test_connection()

def init_db():
    with get_connection() as conn:
        with conn.cursor() as cursor:

            # Enable pgvector
            cursor.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;
            """)

            # Create table for PDF chunks and embeddings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    source TEXT,
                    page INTEGER,
                    embedding VECTOR(3072),
                    UNIQUE(content_hash)
                );
            """)

            # Ensure `content_hash` column and unique index exist for deduplication
            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'document_chunks' AND column_name = 'content_hash'
                    ) THEN
                        ALTER TABLE document_chunks ADD COLUMN content_hash TEXT;
                    END IF;
                END$$;
            """)

            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS document_chunks_content_hash_idx
                ON document_chunks (content_hash);
            """)

        conn.commit()