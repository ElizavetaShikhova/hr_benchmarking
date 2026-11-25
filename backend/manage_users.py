from argparse import ArgumentParser
from getpass import getpass
from typing import Optional

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.config import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from backend.database import SessionFactory
from backend.models import AuthSession, User
from backend.models.user import password_hasher


def add_user(session: Session, email: str, password: str) -> Optional[int]:
    return session.scalar(
        insert(User).values(email=email, password_hash=password_hasher.hash(password))
        .on_conflict_do_nothing(index_elements=[User.email]).returning(User.id)
    )


def set_access(session: Session, email: str, is_active: bool) -> Optional[int]:
    user_id = session.scalar(update(User).where(User.email == email).values(is_active=is_active).returning(User.id))
    if user_id is not None and not is_active:
        session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
    return user_id


def main() -> None:
    parser = ArgumentParser(description="Управление доступом пользователей HR Benchmarking")
    parser.add_argument("action", choices=["add", "disable", "enable"])
    parser.add_argument("email")
    args = parser.parse_args()

    try:
        email = TypeAdapter(EmailStr).validate_python(args.email).casefold()
    except ValidationError:
        parser.error("Укажите корректный email.")

    if args.action == "add":
        password = getpass("Пароль: ")
        if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
            parser.error(f"Пароль должен содержать от {MIN_PASSWORD_LENGTH} до {MAX_PASSWORD_LENGTH} символов.")
        if password != getpass("Повторите пароль: "):
            parser.error("Пароли не совпадают.")
        with SessionFactory.begin() as session:
            if add_user(session, email, password) is None:
                parser.error("Аккаунт с таким email уже существует.")
        print(f"Аккаунт {email} добавлен.")
        return

    is_active = args.action == "enable"
    with SessionFactory.begin() as session:
        if set_access(session, email, is_active) is None:
            parser.error("Аккаунт с таким email не найден.")
    state = "включён" if is_active else "отключён"
    print(f"Доступ для {email} {state}.")


if __name__ == "__main__":
    main()
