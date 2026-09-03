from fastapi import HTTPException, Header, Request, status
from typing import Optional


class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Authorization required"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


VALID_ROLES = {"ADMIN", "FINANCE_CONTROLLER", "REVIEWER", "VIEWER"}


def get_user_role(x_user_role: Optional[str] = Header(default=None)) -> str:
    if x_user_role and x_user_role in VALID_ROLES:
        return x_user_role
    return "VIEWER"


def require_role(allowed_roles: set[str]):
    def decorator(func):
        return func
    return decorator
