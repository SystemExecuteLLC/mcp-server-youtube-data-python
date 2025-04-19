"""
Tool for listing videos from a specific YouTube channel.
"""

from typing import Any, Dict
from api_client import make_youtube_request
from utils import safe_get, truncate_text, resolve_channel_identifier
from constants import MAX_RESULTS_LIMIT

async def list_channel_videos(channel_id: str, max_results: int = 10) -> Dict[str, Any]:
    """List videos from a specific YouTube channel.
    
    Args:
        channel_id: The ID or handle of the YouTube channel
        max_results: Maximum number of results to return (default: 10, max: 50)
        
    Returns:
        Dict containing formatted video list or error
    """
    # Cap max_results to API limit
    max_results = min(max_results, MAX_RESULTS_LIMIT["videos"])
    
    # Resolve channel ID from handle if necessary
    resolved_id = await resolve_channel_identifier(channel_id)
    if resolved_id is None:
        return {"error": f"Could not resolve channel identifier: {channel_id}. Please provide a valid channel ID or handle."}
    
    # First, we need to get the uploads playlist ID for the channel
    channel_params = {
        "part": "contentDetails",
        "id": resolved_id
    }
    
    channel_data = await make_youtube_request("channels", channel_params)
    
    if "error" in channel_data:
        return {"error": channel_data["error"]}
    
    if "items" not in channel_data or not channel_data["items"]:
        return {"error": "Channel not found or error fetching channel information."}
    
    uploads_playlist_id = safe_get(
        channel_data["items"][0],
        "contentDetails",
        "relatedPlaylists",
        "uploads"
    )
    
    if not uploads_playlist_id:
        return {"error": "Could not find uploads playlist for this channel."}
    
    # Now get the videos from the uploads playlist
    playlist_params = {
        "part": "snippet",
        "playlistId": uploads_playlist_id,
        "maxResults": max_results
    }
    
    playlist_data = await make_youtube_request("playlistItems", playlist_params)
    
    if "error" in playlist_data:
        return {"error": playlist_data["error"]}
    
    if "items" not in playlist_data or not playlist_data["items"]:
        return {"error": "No videos found or error fetching videos."}
    
    results = []
    for i, item in enumerate(playlist_data["items"], 1):
        snippet = safe_get(item, "snippet", default={})
        title = safe_get(snippet, "title", default="Unknown")
        published_at = safe_get(snippet, "publishedAt", default="Unknown")
        video_id = safe_get(snippet, "resourceId", "videoId", default="Unknown")
        description = safe_get(snippet, "description", default="No description available")
        
        results.append(
            f"{i}. {title}\n"
            f"   Published: {published_at}\n"
            f"   Video ID: {video_id}\n"
            f"   Description: {truncate_text(description)}\n"
        )
    
    return {"result": "\n".join(results)}
