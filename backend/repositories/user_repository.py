from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User


class UserRepository:
    """
    Handles all DB operations for User model.
    Fully async — no blocking calls, no run_in_executor.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email_or_username(self, email: str, username: str) -> User | None:
        """Single query — checks both email and username in one round trip."""
        result = await self.db.execute(
            select(User).where(
                or_(User.email == email, User.username == username)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Saves new user — returns persisted user with ID."""
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def save(self, user: User) -> User:
        """Saves changes to existing user — used for updates."""
        await self.db.commit()
        await self.db.refresh(user)
        return user