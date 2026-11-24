from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.v1.dependencies import CurrentUserDep, WorkspaceServiceDep
from app.core.constants import DEFAULT_PAGE_LIMIT, DEFAULT_PAGE_OFFSET, MAX_PAGE_LIMIT
from app.core.openapi import error_responses
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
    description=(
        "Create a workspace and automatically enroll the authenticated user as its "
        "`OWNER` in `workspace_members`."
    ),
    responses=error_responses(401, 403),
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
    description=(
        "Return workspaces where the user is a member (or all workspaces for global `ADMIN`)."
    ),
    responses=error_responses(401, 403),
)
async def list_workspaces(
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of workspaces to skip"),
    ] = DEFAULT_PAGE_OFFSET,
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_LIMIT, description="Maximum workspaces to return"),
    ] = DEFAULT_PAGE_LIMIT,
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
    description="Retrieve workspace metadata by UUID. Requires membership in the workspace.",
    responses=error_responses(401, 403, 404),
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
    description=(
        "Update workspace name or description. Restricted to the workspace `OWNER` "
        "or global `ADMIN`."
    ),
    responses=error_responses(401, 403, 404),
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
    description=(
        "Delete a workspace and cascade-delete its memberships, projects, and tasks. "
        "Restricted to the workspace `OWNER` or global `ADMIN`."
    ),
    responses=error_responses(401, 403, 404),
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
    description="List all members and their assigned roles inside the workspace.",
    responses=error_responses(401, 403, 404),
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
    description=(
        "Invite a user to a workspace or update their existing workspace role. "
        "Restricted to workspace `OWNER`/`ADMIN` or global `ADMIN`."
    ),
    responses=error_responses(400, 401, 403, 404, 409),
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
    description=(
        "Remove a user from a workspace. The workspace `OWNER` cannot be removed (409 Conflict)."
    ),
    responses=error_responses(401, 403, 404, 409),
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
    description="Create a new `ACTIVE` project inside the specified workspace.",
    responses=error_responses(401, 403, 404),
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
    description="List projects belonging to the specified workspace with pagination.",
    responses=error_responses(401, 403, 404),
)
async def list_projects_in_workspace(
    workspace_id: UUID,
    current_user: CurrentUserDep,
    service: WorkspaceServiceDep,
    offset: Annotated[int, Query(ge=0, description="Number of projects to skip")] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_LIMIT, description="Maximum projects to return"),
    ] = DEFAULT_PAGE_LIMIT,
) -> list[ProjectResponse]:
    return await service.list_projects(
        workspace_id,
        current_user=current_user,
        offset=offset,
        limit=limit,
    )


