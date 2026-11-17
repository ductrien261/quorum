from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import User

bearer = HTTPBearer(auto_error=False)


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode())
    except ValueError:
        return False


def create_token(user_id: int) -> str:
    st = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(days=st.jwt_expire_days)
    return jwt.encode({"sub": str(user_id), "exp": exp}, st.jwt_secret, algorithm="HS256")


def _decode(token: str) -> int | None:
    try:
        return int(jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])["sub"])
    except Exception:  # noqa: BLE001
        return None


def optional_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User | None:
    if not cred:
        return None
    uid = _decode(cred.credentials)
    return db.get(User, uid) if uid else None


def current_user(user: User | None = Depends(optional_user)) -> User:
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bạn cần đăng nhập để dùng tính năng này.")
    return user
