from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings


class Database:
    _client: AsyncIOMotorClient | None = None
    _db: AsyncIOMotorDatabase | None = None

    @classmethod
    def connect(cls) -> AsyncIOMotorDatabase:
        if cls._client is None:
            cls._client = AsyncIOMotorClient(settings.MONGODB_URI)
            cls._db = cls._client[settings.MONGODB_DB]
        return cls._db

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        if cls._db is None:
            return cls.connect()
        return cls._db

    @classmethod
    async def close(cls) -> None:
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._db = None


def get_db() -> AsyncIOMotorDatabase:
    return Database.get_db()
