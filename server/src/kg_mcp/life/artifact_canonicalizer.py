import re
from typing import Dict, Optional
from urllib.parse import urlparse, urlunparse


TICKET_PATTERN = re.compile(r"\b([A-Z]{2,10}-\d{1,6})\b")


def _normalize_url(raw: str) -> str:
    try:
        parsed = urlparse(raw.strip())
    except Exception:
        return raw.strip()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    scheme = parsed.scheme.lower() or "https"
    return urlunparse((scheme, netloc, path, "", "", ""))


def _infer_artifact_type(app: str, url_or_path: str) -> str:
    app_lower = (app or "").lower()
    if url_or_path.startswith("http"):
        return "web"
    if any(k in app_lower for k in ["mail", "outlook", "gmail"]):
        return "email"
    if any(k in app_lower for k in ["slack", "teams", "discord", "telegram"]):
        return "chat"
    if any(k in app_lower for k in ["jira", "linear", "trello", "asana"]):
        return "ticket"
    if any(k in app_lower for k in ["figma", "notion", "docs", "word"]):
        return "doc"
    if any(k in app_lower for k in ["excel", "sheets", "numbers"]):
        return "sheet"
    if any(k in app_lower for k in ["xcode", "vscode", "jetbrains", "pycharm", "intellij"]):
        return "ide"
    return "unknown"


def canonicalize_artifact(
    artifact: Dict[str, Optional[str]],
    app: str = "",
    window_title: str = "",
) -> Dict[str, Optional[str]]:
    """
    Normalize artifact fields and ensure a stable canonical_id when possible.
    """
    normalized = dict(artifact or {})
    canonical_id = (normalized.get("canonical_id") or "").strip()
    url_or_path = (normalized.get("url_or_path") or "").strip()

    if not canonical_id and url_or_path:
        if url_or_path.startswith("http"):
            canonical_id = f"url:{_normalize_url(url_or_path)}"
        elif url_or_path.startswith("/"):
            canonical_id = f"path:{url_or_path}"

    if not canonical_id and window_title:
        match = TICKET_PATTERN.search(window_title)
        if match:
            canonical_id = f"ticket:{match.group(1)}"

    if canonical_id:
        canonical_id = canonical_id.strip()

    artifact_type = (normalized.get("type") or "").strip().lower()
    if artifact_type in ("", "unknown"):
        inferred = _infer_artifact_type(app, url_or_path)
        artifact_type = inferred

    normalized["canonical_id"] = canonical_id
    normalized["type"] = artifact_type
    return normalized
