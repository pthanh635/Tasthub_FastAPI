from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.v1.dependencies import CurrentUserDep, WorkspaceServiceDep
from app.core.constants import DEFAULT_PAGE_LIMIT, DEFAULT_PAGE_OFFSET, MAX_PAGE_LIMIT
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace (creator becomes OWNER)",
)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> WorkspaceResponse:
    return await service.create_workspace(data, current_user=current_user)


@router.get(
    "",
    response_model=list[WorkspaceResponse],
    status_code=status.HTTP_200_OK,
    summary="List workspaces accessible to current user",
)
async def list_workspaces(
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
    offset: Annotated[int, Query(ge=0)] = DEFAULT_PAGE_OFFSET,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
) -> list[WorkspaceResponse]:
    return await service.list_workspaces(
        current_user=current_user,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workspace details (requires workspace membership)",
)
async def get_workspace(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> WorkspaceResponse:
    return await service.get_workspace(workspace_id, current_user=current_user)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update workspace (owner only)",
)
async def update_workspace(
    workspace_id: UUID,
    data: WorkspaceUpdate,
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> WorkspaceResponse:
    return await service.update_workspace(
        workspace_id,
        data,
        current_user=current_user,
    )


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workspace (owner only)",
)
async def delete_workspace(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> Response:
    await service.delete_workspace(workspace_id, current_user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="List members of a workspace",
)
async def list_workspace_members(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> list[WorkspaceMemberResponse]:
    return await service.list_members(workspace_id, current_user=current_user)


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a member or update member role (OWNER/ADMIN only)",
)
async def add_workspace_member(
    workspace_id: UUID,
    data: WorkspaceMemberCreate,
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> WorkspaceMemberResponse:
    return await service.add_or_update_member(
        workspace_id,
        data,
        current_user=current_user,
    )


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from a workspace (OWNER/ADMIN only)",
)
async def remove_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> Response:
    await service.remove_member(
        workspace_id,
        user_id,
        current_user=current_user,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{workspace_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project in workspace (OWNER/ADMIN/EDITOR only)",
)
async def create_project_in_workspace(
    workspace_id: UUID,
    data: ProjectCreate,
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
) -> ProjectResponse:
    return await service.create_project(
        workspace_id,
        data,
        current_user=current_user,
    )


@router.get(
    "/{workspace_id}/projects",
    response_model=list[ProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List projects in workspace (requires workspace membership)",
)
async def list_projects_in_workspace(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
) -> list[ProjectResponse]:
    return await service.list_projects(
        workspace_id,
        current_user=current_user,
        offset=offset,
        limit=limit,
    )

