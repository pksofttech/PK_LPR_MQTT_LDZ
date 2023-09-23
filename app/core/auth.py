from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any, Optional, Union

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import PyJWTError

from pydantic import BaseModel

from app.core import config
from app.core.database import get_async_session, System_User
from app.core.models import System_User_Type
from ..stdio import *
from .utility import get_password_hash, verify_password


class Token(BaseModel):
    access_token: str
    token_type: str


OAUTH_PATH = "/oauth"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=OAUTH_PATH)
router = APIRouter()


async def allowed_permissions(
    db: AsyncSession,
    user: dict,
    permissions: str,
) -> bool:
    _sql = select(System_User_Type.permission_allowed).where(System_User_Type.id == user["system_user_type_id"])
    _allowed = (await db.execute(_sql)).one_or_none()
    print(permissions)
    if _allowed:
        _allowed = _allowed[0].split(",")
        print(_allowed)
        if permissions in _allowed:
            return 1
    return 0


async def get_user(
    db: AsyncSession,
    username: Optional[str],
) -> System_User:
    # return db.query(System_User).filter(System_User.username == username).first()
    # print_warning(f"User {username}")
    user = (await db.execute(select(System_User).where(System_User.username == username))).first()
    if user:
        return user[0]
    else:
        return None


async def get_user_by_id(
    db: AsyncSession,
    user_id: int,
) -> System_User:
    # return db.query(System_User).filter(System_User.username == username).first()
    # print_warning(f"User {username}")
    user = (await db.execute(select(System_User).where(System_User.id == user_id))).first()
    if user:
        return user[0]
    else:
        return None


async def authenticate_user(
    db,
    username: str,
    password: str,
) -> Union[bool, System_User]:
    user = await get_user(db, username)
    print_success(user)
    if not user:
        return False
    print_warning(user.password)
    if not verify_password(password, user.password):
        return False
    return user


async def create_access_token(data: dict, expires_delta: timedelta = None) -> bytes:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        config.API_SECRET_KEY,
        algorithm=config.API_ALGORITHM,
    )
    print(to_encode)
    return encoded_jwt


async def get_jwt_access(token: str = Depends(oauth2_scheme), db=Depends(get_async_session)) -> int:
    credentials_exception = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    expired_exception = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail="Signature has expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            config.API_SECRET_KEY,
            algorithms=[config.API_ALGORITHM],
        )
        # print_success(payload)
        username = payload.get("sub")
        user_id = payload.get("user_id", None)

        if username is None:
            raise credentials_exception
        # token_data = TokenData(username=username)

    except PyJWTError as e:
        print_error(e)
        if str(e) == "Signature has expired":
            raise expired_exception
        else:
            raise credentials_exception

    # user = await get_user(db, username=username)

    if user_id is None:
        raise credentials_exception
    return int(user_id)


async def access_cookie_token(
    request: Request,
    token_name="Authorization",
    db: AsyncSession = Depends(get_async_session),
):
    token = None
    user_id = None
    _cookie_str = request.headers.get("cookie")
    if _cookie_str:
        cookies = _cookie_str.split(";")
        for c in cookies:
            c = c.strip()
            if c.startswith(f"{token_name}=bearer "):
                token = c.split(" ")[1]
                user_id = await get_current_user_id_token(token)
    if user_id:
        # print_success(user_id)
        sql = (
            select(System_User, System_User_Type)
            .where(System_User.id == user_id)
            .join(System_User_Type, (System_User_Type.id == System_User.system_user_type_id))
        )
        row = (await db.execute(sql)).one()
        _System_User: System_User = row[0]
        _System_User_Type: System_User_Type = row[1]
        user = _System_User.__dict__
        user["user_type"] = _System_User_Type.user_type
        return user
    print("RedirectResponse")

    return None


async def get_current_user_id_token(token: str) -> str:
    # print(token)
    try:
        payload = jwt.decode(
            token,
            config.API_SECRET_KEY,
            algorithms=[config.API_ALGORITHM],
        )
        user_id = payload.get("user_id")

    except PyJWTError:
        return None

    return user_id


@router.get("/login_session", tags=["OAuth"])
async def login_session(db=Depends(get_async_session), user_id=Depends(get_jwt_access)):
    user = await get_user_by_id(db, user_id)
    del user.password
    print(user)
    return user


@router.get("/logout_session", tags=["OAuth"])
async def logout_session(user=Depends(get_jwt_access)):
    # access_token_expires = timedelta(seconds=1)
    # print(access_token_expires)
    # access_token = await create_access_token(
    #     data={"sub": user.username},  # type: ignore
    #     expires_delta=access_token_expires,
    # )
    return None


@router.post(OAUTH_PATH, response_model=Token, tags=["OAuth"])
async def login_for_access_token(
    db=Depends(get_async_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> dict[str, Any]:
    user = await authenticate_user(
        db,
        form_data.username,
        form_data.password,
    )
    print_success(user)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(
        minutes=config.API_ACCESS_TOKEN_EXPIRE_MINUTES,
        # seconds=60,
    )
    access_token = await create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires,
    )
    print_success(access_token)
    return {"access_token": access_token, "token_type": "bearer"}
