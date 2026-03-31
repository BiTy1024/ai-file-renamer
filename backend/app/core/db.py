from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import User, UserCreate, UserRole

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def init_db(session: Session) -> None:
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            role=UserRole.ADMIN,
        )
        user = crud.create_user(session=session, user_create=user_in)


def reset_admin(session: Session) -> User:
    """Reset admin account from env vars. Creates if missing, resets password and role if exists."""
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if user:
        from app.core.security import get_password_hash

        user.hashed_password = get_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
        user.role = UserRole.ADMIN
        user.is_active = True
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    else:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            role=UserRole.ADMIN,
        )
        return crud.create_user(session=session, user_create=user_in)
