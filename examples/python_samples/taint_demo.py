"""
Taint Flow Demonstration — intentionally vulnerable patterns for DPX-Py scanning.

This file demonstrates Level 1 (local access path), Level 2 (interprocedural),
and Level 3 (Source->Sink taint) data flows.
"""

import subprocess


def get_user_by_email(email: str, cursor) -> dict:
    """Level 2: user_id propagates from HTTP input -> function param -> SQL sink."""
    query = f"SELECT * FROM users WHERE email = '{email}'"
    cursor.execute(query)  # SINK: SQL injection
    return cursor.fetchone()


def handle_search_request(request, cursor):
    """Level 1+2: Multi-hop taint from HTTP JSON input -> attribute -> subscript -> interprocedural -> SQL."""
    payload = request.json  # ACCESS: attribute
    query_term = payload["search"]  # ACCESS: subscript
    results = get_user_by_email(query_term, cursor)  # CALL: interprocedural
    return results


def run_system_command(request):
    """Level 1: Direct HTTP param -> command injection sink."""
    cmd = request.args.get("cmd")  # SOURCE: HTTP query param
    output = subprocess.run(cmd, shell=True, capture_output=True, check=False)  # SINK: command injection
    return output.stdout


def read_file_by_path(request):
    """Level 1: HTTP param -> path traversal sink."""
    file_path = request.args["filename"]  # SOURCE: HTTP query param subscript
    with open(file_path, "r") as f:  # SINK: path traversal
        return f.read()


def log_sensitive_data(request, logger):
    """Level 1: Sensitive data -> log sink."""
    password = request.json.get("password")  # SOURCE: sensitive field
    logger.info(f"Login attempt with password: {password}")  # SINK: sensitive data leak


def safe_handler(request, cursor):
    """Clean function — no taint flows. Uses parameterized queries."""
    raw_term = request.json.get("q", "")
    sanitized = raw_term.strip().lower()[:100]
    cursor.execute("SELECT * FROM items WHERE name = %s", (sanitized,))
    return cursor.fetchall()
