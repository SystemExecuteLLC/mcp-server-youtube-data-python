"""
Tool for retrieving channels that a specified channel is subscribed to.
"""

from typing import Any, Dict
from api_client import make_youtube_request
from utils import safe_get, truncate_text, resolve_channel_identifier
from constants import MAX_RESULTS_LIMIT

async def get_channel_subscriptions(channel_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Get a list of channels that the specified channel is subscribed to.
    Note: This requires OAuth authorization and can only be used with the 
    channel of the authorized user, not arbitrary channels.
    
    Args:
        channel_id: The ID or handle of the YouTube channel (must be authorized user's channel)
        max_results: Maximum number of results to return (default: 10, max: 50)
        
    Returns:
        Dict containing formatted subscription list or error
    """
    # Resolve channel ID from handle if necessary
    resolved_id = await resolve_channel_identifier(channel_id)
    if resolved_id is None:
        return {"error": f"Could not resolve channel identifier: {channel_id}. Please provide a valid channel ID or handle."}
    
    params = {
        "part": "snippet",
        "channelId": resolved_id,
        "maxResults": min(max_results, MAX_RESULTS_LIMIT["search"]),
        "order": "alphabetical"
    }
    
    data = await make_youtube_request("subscriptions", params)
    
    if "error" in data:
        if isinstance(data["error"], dict) and "message" in data["error"]:
            error_message = data["error"]["message"]
        else:
            error_message = str(data["error"])
        return {
            "error": (
                f"API Error: {error_message}\n\n"
                "Note: This function requires OAuth authentication and only works "
                "with the authenticated user's channel."
            )
        }
    
    if "items" not in data or not data["items"]:
        return {"error": "No subscriptions found or this channel's subscriptions are private."}
    
    results = [f"Subscriptions for channel {channel_id}:"]
    for i, item in enumerate(data["items"], 1):
        snippet = safe_get(item, "snippet", default={})
        title = safe_get(snippet, "title", default="Unknown")
        channel_id = safe_get(snippet, "resourceId", "channelId", default="Unknown")
        description = safe_get(snippet, "description", default="No description")
        
        results.append(
            f"{i}. {title} (ID: {channel_id})\n"
            f"   {truncate_text(description)}"
        )
    
    return {"result": "\n".join(results)}
