def build_execution_name(prefix: str, search_id: str, user_id: str) -> str:
    """
    Build a unique execution name for Step Functions.

    Args:
        prefix: Execution name prefix (e.g., "search-exec")
        search_id: Unique search identifier
        user_id: User identifier

    Returns:
        Formatted execution name
    """
    # Truncate user_id if too long to keep execution name within AWS limits
    truncated_user_id = user_id[:20] if len(user_id) > 20 else user_id

    # Remove any special characters that aren't allowed in execution names
    safe_user_id = ''.join(c for c in truncated_user_id if c.isalnum() or c in '-_')

    return f"{prefix}-{search_id[:8]}-{safe_user_id}"