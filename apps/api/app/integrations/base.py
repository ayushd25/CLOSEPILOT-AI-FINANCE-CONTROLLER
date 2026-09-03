from typing import Protocol

from app.domain.models import FinancialRecord


class FinancialDataSource(Protocol):
    def fetch_records(self) -> list[FinancialRecord]:
        ...
