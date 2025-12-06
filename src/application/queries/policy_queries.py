from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID

from .base import QueryHandler, PaginationParams
from src.infrastructure.queries.policy_queries import (
    PolicyQueries,
    PolicyRepositoryView,
    PolicyView,
)


@dataclass(frozen=True)
class GetPolicyRepositoryById:
    repository_id: UUID


@dataclass(frozen=True)
class ListPolicyRepositories:
    pagination: PaginationParams = None

    def __post_init__(self):
        object.__setattr__(self, 'pagination', self.pagination or PaginationParams())


@dataclass(frozen=True)
class GetPoliciesByRepository:
    repository_id: UUID
    requirement_type: Optional[str] = None


@dataclass(frozen=True)
class CountPolicyRepositories:
    pass


class GetPolicyRepositoryByIdHandler(QueryHandler[GetPolicyRepositoryById, Optional[PolicyRepositoryView]]):
    def __init__(self, policy_queries: PolicyQueries):
        self._queries = policy_queries

    async def handle(self, query: GetPolicyRepositoryById) -> Optional[PolicyRepositoryView]:
        return await self._queries.get_repository_by_id(query.repository_id)


class ListPolicyRepositoriesHandler(QueryHandler[ListPolicyRepositories, List[PolicyRepositoryView]]):
    def __init__(self, policy_queries: PolicyQueries):
        self._queries = policy_queries

    async def handle(self, query: ListPolicyRepositories) -> List[PolicyRepositoryView]:
        return await self._queries.list_repositories(
            limit=query.pagination.limit,
            offset=query.pagination.offset
        )


class GetPoliciesByRepositoryHandler(QueryHandler[GetPoliciesByRepository, List[PolicyView]]):
    def __init__(self, policy_queries: PolicyQueries):
        self._queries = policy_queries

    async def handle(self, query: GetPoliciesByRepository) -> List[PolicyView]:
        return await self._queries.get_policies_by_repository(
            repository_id=query.repository_id,
            requirement_type=query.requirement_type
        )


class CountPolicyRepositoriesHandler(QueryHandler[CountPolicyRepositories, int]):
    def __init__(self, policy_queries: PolicyQueries):
        self._queries = policy_queries

    async def handle(self, query: CountPolicyRepositories) -> int:
        return await self._queries.count_repositories()
