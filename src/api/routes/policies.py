from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status

from src.api.schemas.policies import (
    PolicyRepositoryResponse,
    PolicyRepositoryListResponse,
    PolicyRepositoryCreate,
    PolicyRepositoryUpdate,
    PolicyResponse,
    PolicyListResponse,
    PolicyCreate,
    PolicyUpdate,
    ComplianceStatusResponse,
)
from src.api.dependencies import (
    get_create_policy_repository_handler,
    get_add_policy_handler,
    get_assign_document_handler,
    get_policy_repository_handler,
    get_list_policy_repositories_handler,
    get_policies_handler,
    get_document_by_id_handler,
)
from src.domain.commands import CreatePolicyRepository, AddPolicy, AssignDocumentToPolicy
from src.application.queries.policy_queries import (
    GetPolicyRepositoryById,
    ListPolicyRepositories,
    GetPoliciesByRepository,
)
from src.application.queries.base import PaginationParams
from src.application.queries.document_queries import GetDocumentById

router = APIRouter()


@router.post("/policy-repositories", response_model=PolicyRepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_repository(
    request: PolicyRepositoryCreate,
    create_handler=Depends(get_create_policy_repository_handler),
    query_handler=Depends(get_policy_repository_handler),
):
    command = CreatePolicyRepository(
        name=request.name,
        description=request.description or "",
        created_by="anonymous",
    )

    repository_id = await create_handler.handle(command)
    
    query = GetPolicyRepositoryById(repository_id=repository_id)
    repository = await query_handler.handle(query)
    
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Policy repository created but could not be retrieved",
        )

    return PolicyRepositoryResponse(
        id=repository.id,
        name=repository.name,
        description=repository.description,
        policy_count=repository.policy_count,
        document_count=repository.document_count,
        created_at=repository.created_at,
        updated_at=repository.updated_at,
    )


@router.get("/policy-repositories", response_model=PolicyRepositoryListResponse)
async def list_policy_repositories(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    handler=Depends(get_list_policy_repositories_handler),
):
    query = ListPolicyRepositories(
        pagination=PaginationParams(
            limit=per_page,
            offset=(page - 1) * per_page,
        )
    )

    repositories = await handler.handle(query)

    return PolicyRepositoryListResponse(
        repositories=[
            PolicyRepositoryResponse(
                id=repo.id,
                name=repo.name,
                description=repo.description,
                policy_count=repo.policy_count,
                document_count=repo.document_count,
                created_at=repo.created_at,
                updated_at=repo.updated_at,
            )
            for repo in repositories
        ],
        total=len(repositories),
    )


@router.get("/policy-repositories/{repository_id}", response_model=PolicyRepositoryResponse)
async def get_policy_repository(
    repository_id: UUID,
    handler=Depends(get_policy_repository_handler),
):
    query = GetPolicyRepositoryById(repository_id=repository_id)
    repository = await handler.handle(query)

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy repository with ID {repository_id} not found",
        )

    return PolicyRepositoryResponse(
        id=repository.id,
        name=repository.name,
        description=repository.description,
        policy_count=repository.policy_count,
        document_count=repository.document_count,
        created_at=repository.created_at,
        updated_at=repository.updated_at,
    )


@router.patch("/policy-repositories/{repository_id}", response_model=PolicyRepositoryResponse)
async def update_policy_repository(
    repository_id: UUID,
    request: PolicyRepositoryUpdate,
    handler=Depends(get_policy_repository_handler),
):
    query = GetPolicyRepositoryById(repository_id=repository_id)
    repository = await handler.handle(query)

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy repository with ID {repository_id} not found",
        )

    return PolicyRepositoryResponse(
        id=repository.id,
        name=request.name or repository.name,
        description=request.description if request.description is not None else repository.description,
        policy_count=repository.policy_count,
        document_count=repository.document_count,
        created_at=repository.created_at,
        updated_at=repository.updated_at,
    )


@router.delete("/policy-repositories/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy_repository(
    repository_id: UUID,
    handler=Depends(get_policy_repository_handler),
):
    query = GetPolicyRepositoryById(repository_id=repository_id)
    repository = await handler.handle(query)

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy repository with ID {repository_id} not found",
        )

    if repository.document_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete policy repository with assigned documents",
        )

    return None


@router.post("/policy-repositories/{repository_id}/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def add_policy(
    repository_id: UUID,
    request: PolicyCreate,
    add_handler=Depends(get_add_policy_handler),
    repo_handler=Depends(get_policy_repository_handler),
    policies_handler=Depends(get_policies_handler),
):
    query = GetPolicyRepositoryById(repository_id=repository_id)
    repository = await repo_handler.handle(query)

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy repository with ID {repository_id} not found",
        )

    command = AddPolicy(
        repository_id=repository_id,
        policy_name=request.name,
        policy_content=request.description or "",
        requirement_type=request.requirement_type,
        added_by="anonymous",
    )

    policy_id = await add_handler.handle(command)
    
    policies_query = GetPoliciesByRepository(repository_id=repository_id)
    policies = await policies_handler.handle(policies_query)
    policy = next((p for p in policies if p.id == policy_id), None)
    
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Policy created but could not be retrieved",
        )

    return PolicyResponse(
        id=policy.id,
        repository_id=policy.repository_id,
        name=policy.name,
        description=policy.description,
        requirement_type=policy.requirement_type,
        ai_prompt_template=request.ai_prompt_template,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.get("/policy-repositories/{repository_id}/policies", response_model=PolicyListResponse)
async def list_policies(
    repository_id: UUID,
    policies_handler=Depends(get_policies_handler),
    repo_handler=Depends(get_policy_repository_handler),
):
    query = GetPolicyRepositoryById(repository_id=repository_id)
    repository = await repo_handler.handle(query)

    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy repository with ID {repository_id} not found",
        )

    policies_query = GetPoliciesByRepository(repository_id=repository_id)
    policies = await policies_handler.handle(policies_query)

    return PolicyListResponse(
        policies=[
            PolicyResponse(
                id=policy.id,
                repository_id=policy.repository_id,
                name=policy.name,
                description=policy.description,
                requirement_type=policy.requirement_type,
                created_at=policy.created_at,
                updated_at=policy.updated_at,
            )
            for policy in policies
        ],
        total=len(policies),
    )


@router.get("/policy-repositories/{repository_id}/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    repository_id: UUID,
    policy_id: UUID,
    policies_handler=Depends(get_policies_handler),
):
    policies_query = GetPoliciesByRepository(repository_id=repository_id)
    policies = await policies_handler.handle(policies_query)

    policy = next((p for p in policies if p.id == policy_id), None)

    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {policy_id} not found",
        )

    return PolicyResponse(
        id=policy.id,
        repository_id=policy.repository_id,
        name=policy.name,
        description=policy.description,
        requirement_type=policy.requirement_type,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.patch("/policy-repositories/{repository_id}/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    repository_id: UUID,
    policy_id: UUID,
    request: PolicyUpdate,
    policies_handler=Depends(get_policies_handler),
):
    policies_query = GetPoliciesByRepository(repository_id=repository_id)
    policies = await policies_handler.handle(policies_query)

    policy = next((p for p in policies if p.id == policy_id), None)

    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {policy_id} not found",
        )

    return PolicyResponse(
        id=policy.id,
        repository_id=policy.repository_id,
        name=request.name or policy.name,
        description=request.description if request.description is not None else policy.description,
        requirement_type=request.requirement_type or policy.requirement_type,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.delete("/policy-repositories/{repository_id}/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_policy(
    repository_id: UUID,
    policy_id: UUID,
    policies_handler=Depends(get_policies_handler),
):
    policies_query = GetPoliciesByRepository(repository_id=repository_id)
    policies = await policies_handler.handle(policies_query)

    policy = next((p for p in policies if p.id == policy_id), None)

    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {policy_id} not found",
        )

    return None


@router.get("/documents/{document_id}/compliance", response_model=ComplianceStatusResponse)
async def get_compliance_status(
    document_id: UUID,
    document_handler=Depends(get_document_by_id_handler),
):
    query = GetDocumentById(document_id=document_id)
    document = await document_handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    import datetime
    return ComplianceStatusResponse(
        document_id=document_id,
        status=document.compliance_status or "pending",
        checked_at=datetime.datetime.utcnow(),
    )
