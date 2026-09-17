import json
from typing import Any
from urllib.parse import unquote, urlparse

import pymysql
from pymysql.cursors import DictCursor


def connect(database_url: str):
    """Open a connection to the backend MySQL database."""
    url = urlparse(database_url)
    if url.scheme != "mysql" or not url.hostname or not url.path:
        raise ValueError("DATABASE_URL must be a valid mysql:// URL")

    parameters = dict(item.split("=", 1) for item in url.query.split("&") if "=" in item)
    ssl_accept = parameters.get("sslaccept")
    ssl_cert = unquote(parameters["sslcert"]) if parameters.get("sslcert") else None
    ssl = None
    if ssl_accept == "strict" or ssl_cert:
        ssl = {"check_hostname": True}
        if ssl_cert:
            ssl["ca"] = ssl_cert

    return pymysql.connect(
        host=url.hostname,
        port=url.port or 3306,
        user=unquote(url.username or ""),
        password=unquote(url.password or ""),
        database=unquote(url.path.lstrip("/")),
        ssl=ssl,
        connect_timeout=10,
        read_timeout=15,
        write_timeout=15,
        cursorclass=DictCursor,
    )


def parse_indicators(scam_case: dict[str, Any]) -> dict[str, Any]:
    if isinstance(scam_case["indicators"], str):
        scam_case["indicators"] = json.loads(scam_case["indicators"])
    return scam_case


def get_scam_case(database_url: str, case_id: int) -> dict[str, Any]:
    """Load one ScamCase from the backend MySQL database."""
    connection = connect(database_url)
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

    return parse_indicators(scam_case)


def list_scam_cases(database_url: str, verified_only: bool = True) -> list[dict[str, Any]]:
    """Load scam cases for indexing, optionally limited to verified records."""
    connection = connect(database_url)
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT id, title, scamType, description, sampleText, indicators,
                       riskLevel, source, verified
                FROM ScamCase
            """
            if verified_only:
                query += " WHERE verified = TRUE"
            query += " ORDER BY id"
            cursor.execute(query)
            scam_cases = cursor.fetchall()
    finally:
        connection.close()

    return [parse_indicators(scam_case) for scam_case in scam_cases]
