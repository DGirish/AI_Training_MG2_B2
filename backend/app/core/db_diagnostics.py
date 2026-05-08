from __future__ import annotations

import logging

from fastapi import HTTPException, status


logger = logging.getLogger(__name__)


def classify_db_exception(exc: Exception) -> str:
    message = str(exc).lower()

    if "getaddrinfo" in message or "name or service not known" in message or "nodename nor servname" in message:
        return "dns_resolution"
    if "connection timeout" in message or "timed out" in message or "timeout expired" in message:
        return "network_timeout"
    if "too many clients" in message or "max client" in message or "pool" in message:
        return "pool_exhaustion"
    if "ssl" in message or "certificate" in message or "tls" in message:
        return "ssl_tls"
    if "password authentication failed" in message or "authentication failed" in message:
        return "auth_failure"

    return "unknown"


def db_unavailable_http_error(context: str, exc: Exception, detail: str) -> HTTPException:
    category = classify_db_exception(exc)
    logger.exception("DB failure in %s (category=%s): %s", context, category, exc)
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=detail,
    )
