"""Small security helpers shared by the blueprints."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

from flask import request, url_for

from app.models import Role, User

# Which dashboard each role belongs to.
DASHBOARD_ENDPOINTS = {
    Role.ADMIN: "admin.dashboard",
    Role.DOCTOR: "doctor.dashboard",
    Role.PATIENT: "patient.dashboard",
}


def dashboard_url(user: User) -> str:
    """Return the dashboard URL for a user's role.

    Used after login, after registration and in the navbar, so the mapping
    exists in exactly one place.
    """
    endpoint = DASHBOARD_ENDPOINTS.get(user.role)
    if endpoint is None:  # pragma: no cover - the role CHECK constraint blocks this
        return url_for("main.index")
    return url_for(endpoint)


def is_safe_redirect(target: str | None) -> bool:
    """True only for relative URLs on this same host.

    Protects the `?next=` parameter from becoming an open redirect
    (e.g. /auth/login?next=https://evil.example/login).
    """
    if not target:
        return False

    reference = urlparse(request.host_url)
    candidate = urlparse(urljoin(request.host_url, target))

    return candidate.scheme in ("http", "https") and candidate.netloc == reference.netloc
