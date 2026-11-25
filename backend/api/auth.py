from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.schemas import AccessToken, Credentials, ErrorResponse, UserProfile
from backend.config import AUTH_SESSION_LIFETIME_SECONDS
from backend.database import get_session
from backend.models import AuthSession, User
from backend.models.user import password_hasher


class AuthRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        handle = super().get_route_handler()

        async def handle_request(request: Request) -> Response:
            try:
                return await handle(request)
            except RequestValidationError as exc:
                errors = [{"type": error["type"], "loc": error["loc"], "msg": error["msg"]}
                          for error in exc.errors()]
                raise RequestValidationError(errors) from None

        return handle_request


auth_router = APIRouter(prefix="/auth", tags=["auth"], route_class=AuthRoute, responses={401: {"model": ErrorResponse}})
bearer = HTTPBearer(auto_error=False, scheme_name="BearerAuth")
DUMMY_PASSWORD_HASH = password_hasher.hash(token_urlsafe(32))
SessionDep = Annotated[Session, Depends(get_session)]
BearerCredentials = Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer)]


def unauthorized(detail: str = "Требуется вход в аккаунт.") -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def get_current_session(credentials: BearerCredentials, session: SessionDep) -> AuthSession:
    if credentials is None:
        raise unauthorized()
    auth_session = session.scalar(select(AuthSession).join(User).where(
        AuthSession.token_hash == hash_token(credentials.credentials),
        AuthSession.expires_at > func.now(),
        User.is_active.is_(True),
    ))
    if auth_session is None:
        raise unauthorized()
    return auth_session


CurrentSession = Annotated[AuthSession, Depends(get_current_session)]


@auth_router.post("/login")
def login(credentials: Credentials, session: SessionDep, response: Response) -> AccessToken:
    user = session.scalar(select(User).where(
        User.email == credentials.email.casefold(), User.is_active.is_(True),
    ).with_for_update())
    password_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    matches = password_hasher.verify(credentials.password.get_secret_value(), password_hash)
    if user is None or not matches:
        raise unauthorized("Неверный email или пароль.")

    token = token_urlsafe(32)
    session.add(AuthSession(
        token_hash=hash_token(token), user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=AUTH_SESSION_LIFETIME_SECONDS),
    ))
    session.commit()
    response.headers["Cache-Control"] = "no-store"
    return AccessToken(access_token=token, expires_in=AUTH_SESSION_LIFETIME_SECONDS)


@auth_router.get("/me")
def get_profile(current_session: CurrentSession, session: SessionDep) -> UserProfile:
    user = session.get(User, current_session.user_id)
    if user is None:
        raise unauthorized()
    return UserProfile.model_validate(user)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_session: CurrentSession, session: SessionDep) -> Response:
    session.delete(current_session)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
