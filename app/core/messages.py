class ErrorMessages:
    """Centralized domain and HTTP error messages."""

    # Authentication (401)
    NOT_AUTHENTICATED = "Not authenticated"
    INVALID_CREDENTIALS = "Invalid email or password"
    INVALID_OR_EXPIRED_TOKEN = "Invalid or expired token"
    INVALID_TOKEN_TYPE = "Invalid token type"
    MALFORMED_TOKEN_PAYLOAD = "Malformed token payload"
    REFRESH_TOKEN_REVOKED_OR_EXPIRED = "Refresh token has been revoked or expired"
    REFRESH_TOKEN_INVALID = "Refresh token is invalid"
    USER_NOT_FOUND_FOR_TOKEN = "User associated with token no longer exists"

    # Authorization / Permission (403)
    INACTIVE_USER = "Inactive user"
    PERMISSION_DENIED = "You do not have permission to perform this action"
    GLOBAL_ADMIN_REQUIRED = "Admin privileges are required for this action"
    WORKSPACE_PERMISSION_DENIED = (
        "You do not have sufficient permissions in this workspace"
    )
    WORKSPACE_OWNER_REQUIRED = (
        "Only the workspace owner or a global admin can perform this action"
    )
    TASK_DELETE_FORBIDDEN = (
        "Only the task creator or a workspace owner/admin can delete this task"
    )
    REFRESH_TOKEN_OWNERSHIP_MISMATCH = (
        "Cannot revoke a refresh token belonging to another user"
    )

    # Conflict (409)
    EMAIL_ALREADY_REGISTERED = "A user with this email already exists"
    WORKSPACE_MEMBER_ALREADY_EXISTS = "User is already a member of this workspace"
    CANNOT_DOWNGRADE_WORKSPACE_OWNER = "Cannot downgrade the workspace owner's role"
    CANNOT_REMOVE_WORKSPACE_OWNER = "Cannot remove the workspace owner from workspace"
    CANNOT_DELETE_LAST_ACTIVE_ADMIN = (
        "Cannot delete or deactivate the last active admin user"
    )
    CANNOT_DELETE_USER_WITH_RESOURCES = (
        "Cannot delete user who owns workspaces or has dependent resources"
    )
    CANNOT_DELETE_WORKSPACE_WITH_RESOURCES = (
        "Cannot delete workspace with dependent resources"
    )

    # Bad Request / Business Validation (400)
    INCORRECT_CURRENT_PASSWORD = "Current password is incorrect"
    NEW_PASSWORD_SAME_AS_OLD = "New password must be different from current password"
    CANNOT_DELETE_SELF = "Users cannot delete their own account"
    CANNOT_DEACTIVATE_OR_DEMOTE_SELF = (
        "Admins cannot deactivate or demote their own account"
    )
    CANNOT_ASSIGN_OWNER_ROLE = "Cannot assign OWNER role to a non-owner member"
    PROJECT_ARCHIVED = "Cannot create tasks in an archived project"
    ASSIGNEE_NOT_IN_WORKSPACE = "Assignee must be a member of the project's workspace"
