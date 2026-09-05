"""In-memory document store used as the ClosePilot persistence layer.

Exposes an async, MongoDB-like collection API (``find_one`` / ``find`` /
``insert_one`` / ``update_one`` / ``delete_many`` / ``count_documents`` /
``create_index``) so application code never needs to change. All data lives
in-process: the app operates entirely on synthetic data, so nothing else is
required. On render/restart the store is empty and data is regenerated.
"""

from __future__ import annotations

import copy
import re
import secrets
from typing import Any, AsyncIterator, Optional

_OPERATORS = {"$eq", "$ne", "$gt", "$gte", "$lt", "$lte", "$in", "$nin", "$regex", "$options", "$exists"}


def _new_id() -> str:
    return secrets.token_hex(12)  # 24-char hex id, ObjectId-style length


def _field_matches(doc_value: Any, condition: Any) -> bool:
    """Match a single field value against a scalar or operator expression."""
    if isinstance(condition, dict) and any(k in _OPERATORS for k in condition):
        ops = dict(condition)
        options = ops.get("$options")
        for op, expected in ops.items():
            if op == "$options":
                continue
            if op == "$eq":
                if doc_value != expected:
                    return False
            elif op == "$ne":
                if doc_value == expected:
                    return False
            elif op == "$in":
                if doc_value not in expected:
                    return False
            elif op == "$nin":
                if doc_value in expected:
                    return False
            elif op == "$exists":
                expected_bool = bool(expected)
                if (doc_value is not None) != expected_bool:
                    return False
            elif op == "$regex":
                flags = re.IGNORECASE if options and "i" in options else 0
                if doc_value is None or not re.search(str(expected), str(doc_value), flags):
                    return False
            elif op in ("$gt", "$gte", "$lt", "$lte"):
                if doc_value is None:
                    return False
                if op == "$gt" and not (doc_value > expected):
                    return False
                if op == "$gte" and not (doc_value >= expected):
                    return False
                if op == "$lt" and not (doc_value < expected):
                    return False
                if op == "$lte" and not (doc_value <= expected):
                    return False
            else:
                return False
        return True
    return doc_value == condition


def _matches(doc: dict, query: Optional[dict]) -> bool:
    if not query:
        return True
    for key, cond in query.items():
        if key == "$and" and isinstance(cond, list):
            if not all(_matches(doc, q) for q in cond):
                return False
        elif key == "$or" and isinstance(cond, list):
            if not any(_matches(doc, q) for q in cond):
                return False
        elif not _field_matches(doc.get(key), cond):
            return False
    return True


def _apply_update(doc: dict, update: dict) -> None:
    for key, value in update.items():
        if key == "$set":
            for field, val in value.items():
                doc[field] = copy.deepcopy(val)
        elif key == "$unset":
            for field in value:
                doc.pop(field, None)
        else:
            doc[key] = copy.deepcopy(value)


def _sort_value(doc: dict, key: str) -> tuple:
    value = doc.get(key)
    return (value is None, value)


class Cursor:
    """Async cursor over a snapshot of matching documents."""

    def __init__(self, docs: list[dict]):
        self._docs = list(docs)
        self._sort: Optional[list[tuple[str, int]]] = None
        self._skip = 0
        self._limit: Optional[int] = None

    def sort(self, key_or_list, direction: int = 1) -> "Cursor":
        if key_or_list is None:
            return self
        if isinstance(key_or_list, list):
            self._sort = [(k, int(d)) for k, d in key_or_list]
        else:
            self._sort = [(key_or_list, int(direction))]
        return self

    def skip(self, count: int) -> "Cursor":
        self._skip = int(count)
        return self

    def limit(self, count: int) -> "Cursor":
        self._limit = int(count)
        return self

    def _resolved(self) -> list[dict]:
        docs = self._docs
        if self._sort:
            for key, direction in reversed(self._sort):
                docs = sorted(docs, key=lambda d, k=key: _sort_value(d, k), reverse=(direction < 0))
        if self._skip:
            docs = docs[self._skip:]
        if self._limit is not None:
            docs = docs[: self._limit]
        return docs

    async def to_list(self, length: Optional[int] = None) -> list[dict]:
        del length
        return self._resolved()

    def __aiter__(self) -> AsyncIterator[dict]:
        return self._aiter()

    async def _aiter(self) -> AsyncIterator[dict]:
        for doc in self._resolved():
            yield doc


class InsertOneResult:
    def __init__(self, inserted_id: Any):
        self.inserted_id = inserted_id


class UpdateResult:
    def __init__(self, matched_count: int = 0, modified_count: int = 0, upserted_id: Any = None):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.upserted_id = upserted_id


class DeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


class MemoryCollection:
    def __init__(self, name: str, store: dict[str, list[dict]]):
        self._name = name
        self._store = store

    def _docs(self) -> list[dict]:
        return self._store.setdefault(self._name, [])

    def find(self, filter: Optional[dict] = None) -> Cursor:
        return Cursor([doc for doc in self._docs() if _matches(doc, filter)])

    async def find_one(self, filter: Optional[dict] = None, sort: Optional[list] = None, **kwargs) -> Optional[dict]:
        del kwargs
        docs = [doc for doc in self._docs() if _matches(doc, filter)]
        if sort:
            docs = Cursor(docs).sort(sort)._resolved()
        return docs[0] if docs else None

    async def insert_one(self, doc: dict) -> InsertOneResult:
        stored = copy.deepcopy(doc)
        if "_id" not in stored:
            stored["_id"] = _new_id()
        self._docs().append(stored)
        return InsertOneResult(stored["_id"])

    async def insert_many(self, docs: list[dict]) -> list[InsertOneResult]:
        return [await self.insert_one(doc) for doc in docs]

    async def update_one(self, filter: dict, update: dict, upsert: bool = False) -> UpdateResult:
        docs = self._docs()
        for doc in docs:
            if _matches(doc, filter):
                _apply_update(doc, update)
                return UpdateResult(matched_count=1, modified_count=1)
        if upsert:
            new_doc = copy.deepcopy(filter)
            if "_id" not in new_doc:
                new_doc["_id"] = _new_id()
            _apply_update(new_doc, update)
            docs.append(new_doc)
            return UpdateResult(matched_count=0, modified_count=0, upserted_id=new_doc["_id"])
        return UpdateResult()

    async def delete_many(self, filter: Optional[dict] = None) -> DeleteResult:
        docs = self._docs()
        kept = [doc for doc in docs if not _matches(doc, filter)]
        deleted = len(docs) - len(kept)
        self._store[self._name] = kept
        return DeleteResult(deleted)

    async def delete_one(self, filter: Optional[dict] = None) -> DeleteResult:
        docs = self._docs()
        for index, doc in enumerate(docs):
            if _matches(doc, filter):
                del docs[index]
                return DeleteResult(1)
        return DeleteResult(0)

    async def count_documents(self, filter: Optional[dict] = None, **kwargs) -> int:
        del kwargs
        return sum(1 for doc in self._docs() if _matches(doc, filter))

    async def create_index(self, *args, **kwargs):
        del args, kwargs
        return None

    async def drop(self) -> None:
        self._store[self._name] = []


class MemoryDatabase:
    """Mongo-like in-memory database facade."""

    def __init__(self):
        self._store: dict[str, list[dict]] = {}
        self._collections: dict[str, MemoryCollection] = {}

    def _get_collection(self, name: str) -> MemoryCollection:
        if name not in self._collections:
            self._collections[name] = MemoryCollection(name, self._store)
        return self._collections[name]

    def __getattr__(self, name: str) -> MemoryCollection:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._get_collection(name)

    def __getitem__(self, name: str) -> MemoryCollection:
        return self._get_collection(name)

    async def command(self, name: str, *args, **kwargs):
        del name, args, kwargs
        return {"ok": 1}

    def reset(self) -> None:
        self._collections.clear()
        self._store.clear()