from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ..database import get_db
from ..core.security import decode_access_token
from ..models.auth import UserAccount

DbSession = Annotated[Session, Depends(get_db)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> UserAccount:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    email: str | None = payload.get("sub")
    if email is None:
        raise credentials_exception
    user = db.query(UserAccount).filter(UserAccount.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


CurrentUser = Annotated[UserAccount, Depends(get_current_user)]


def require_roles(*roles: str):
    def role_checker(
        current_user: Annotated[UserAccount, Depends(get_current_user)],
    ) -> UserAccount:
        if current_user.role == "admin":
            return current_user
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(roles)}",
            )
        return current_user

    return Depends(role_checker)
