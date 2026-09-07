import json
from typing import Any
from urllib.parse import unquote, urlparse

import pymysql
from pymysql.cursors import DictCursor


def get_scam_case(database_url: str, case_id: int) -> dict[str, Any]:
    """Load one ScamCase from the backend MySQL database."""
    url = urlparse(database_url)
    if url.scheme != "mysql" or not url.hostname or not url.path:
        raise ValueError("DATABASE_URL must be a valid mysql:// URL")

    connection = pymysql.connect(
        host=url.hostname,
        port=url.port or 3306,
        user=unquote(url.username or ""),
        password=unquote(url.password or ""),
        database=unquote(url.path.lstrip("/")),
        cursorclass=DictCursor,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, scamType, description, sampleText, indicators,
                       riskLevel, source, verified
                FROM ScamCase
                WHERE id = %s
                """,
                (case_id,),
            )
            scam_case = cursor.fetchone()
    finally:
        connection.close()

    if scam_case is None:
        raise LookupError(f"ScamCase {case_id} was not found")

    if isinstance(scam_case["indicators"], str):
        scam_case["indicators"] = json.loads(scam_case["indicators"])
    return scam_case
