import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.entities import Organization, OrganizationMember, User

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    organization: Organization
    role: str


class InMemoryRateLimiter:
    """Sliding-window rate limiter per client IP / user."""

    def __init__(self, max_requests: int = 180, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: Dict[str, List[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        now = time.time()
        window_start = now - self.window_seconds
        recent = [ts for ts in self._buckets[key] if ts > window_start]
        if len(recent) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please retry after a short pause.",
            )
        recent.append(now)
        self._buckets[key] = recent


rate_limiter = InMemoryRateLimiter()


def get_current_context(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_nexus_org_id: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthContext:
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limiter.check(client_ip)

    if credentials and credentials.credentials:
        try:
            payload = decode_token(credentials.credentials)
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type.",
                )
            user_id = payload.get("sub")
            org_id = x_nexus_org_id or payload.get("org_id")

            user = (
                db.query(User)
                .filter(User.id == user_id, User.is_active.is_(True))
                .first()
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authenticated user not found or inactive.",
                )

            membership = (
                db.query(OrganizationMember)
                .filter(
                    OrganizationMember.user_id == user.id,
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.status == "active",
                )
                .first()
            )
            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: User is not an active member of the requested organization.",
                )

            org = (
                db.query(Organization)
                .filter(
                    Organization.id == membership.organization_id,
                    Organization.is_active.is_(True),
                )
                .first()
            )
            if not org:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found.",
                )

            return AuthContext(user=user, organization=org, role=membership.role)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired authentication token: {exc}",
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials required.",
    )


def require_roles(*allowed_roles: str):
    def _checker(ctx: AuthContext = Depends(get_current_context)) -> AuthContext:
        if ctx.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Role '{ctx.role}' is not in {list(allowed_roles)}.",
            )
        return ctx

    return _checker

