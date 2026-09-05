from app.db.memory import MemoryDatabase, MemoryCollection


class Database:
    _db: MemoryDatabase | None = None

    @classmethod
    def connect(cls) -> MemoryDatabase:
        if cls._db is None:
            cls._db = MemoryDatabase()
        return cls._db

    @classmethod
    def get_db(cls) -> MemoryDatabase:
        return cls.connect()

    @classmethod
    async def close(cls) -> None:
        cls._db = None

    @classmethod
    def reset(cls) -> None:
        cls._db = MemoryDatabase()


def get_db() -> MemoryDatabase:
    return Database.get_db()