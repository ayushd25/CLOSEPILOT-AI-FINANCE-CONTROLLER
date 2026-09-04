from typing import Any, Optional

from app.db import Database
from app.domain.policy_config import PolicyConfig, default_policy_config
from app.utils import utcnow


class PolicyConfigRepository:
    def __init__(self, db=None):
        self.db = db if db is not None else Database.get_db()
        self.collection = self.db.policy_config
        self._cache: Optional[PolicyConfig] = None

    async def _ensure_seeded(self) -> None:
        if await self.collection.count_documents({}) == 0:
            cfg = default_policy_config()
            await self.collection.insert_one(cfg.to_mongo())

    async def invalidate_cache(self) -> None:
        self._cache = None

    async def get(self) -> PolicyConfig:
        await self._ensure_seeded()
        if self._cache is not None:
            return self._cache
        doc = await self.collection.find_one({"enabled": True})
        if not doc:
            doc = await self.collection.find_one({})
        cfg = PolicyConfig.from_mongo(doc) if doc else default_policy_config()
        self._cache = cfg
        return cfg

    async def update(
        self,
        thresholds: dict[str, Any],
        toggles: dict[str, Any],
        updated_by: str = "system",
        change_note: str = "Policy updated",
    ) -> PolicyConfig:
        await self._ensure_seeded()
        current = await self.get()
        new_thresholds = current.thresholds.model_copy(update=thresholds)
        new_toggles = current.toggles.model_copy(update=toggles)
        cfg = PolicyConfig(
            config_id=current.config_id,
            enabled=True,
            version=current.version + 1,
            thresholds=new_thresholds,
            toggles=new_toggles,
            description=current.description,
            updated_at=utcnow(),
            updated_by=updated_by,
            change_note=change_note,
        )
        await self.collection.update_one(
            {"config_id": current.config_id},
            {"$set": cfg.to_mongo()},
            upsert=True,
        )
        self._cache = cfg
        return cfg