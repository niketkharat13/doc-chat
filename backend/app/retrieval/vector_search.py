from app.database.db import get_connection


def similarity_search(query_vector, limit=5):
    sql = """
        SELECT
            id,
            content,
            source,
            file_name,
            page,
            embedding <=> %s::vector AS distance
        FROM document_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                sql,
                (query_vector, query_vector, limit),
            )

            return cursor.fetchall()