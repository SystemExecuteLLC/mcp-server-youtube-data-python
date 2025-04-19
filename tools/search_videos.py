"""
Tool for searching YouTube videos based on a query.
"""

from typing import Any, Dict
from api_client import make_youtube_request
from utils import safe_get, truncate_text
from constants import MAX_RESULTS_LIMIT

async def search_videos(query: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for YouTube videos based on a query.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 10, max: 50)
        
    Returns:
        Dict containing formatted search results or error
    """
    # Cap max_results to API limit
    max_results = min(max_results, MAX_RESULTS_LIMIT["search"])
    
    params = {
        "part": "snippet",
        "q": query,
        "maxResults": max_results,
        "type": "video"
    }
    
    data = await make_youtube_request("search", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "No videos found or error fetching search results."}
    
    results = []
    for i, item in enumerate(data["items"], 1):
        video_id = safe_get(item, "id", "videoId", default="Unknown")
        snippet = safe_get(item, "snippet", default={})
        title = safe_get(snippet, "title", default="Unknown")
        description = safe_get(snippet, "description", default="No description available")
        channel_title = safe_get(snippet, "channelTitle", default="Unknown")
        published_at = safe_get(snippet, "publishedAt", default="Unknown")
        
        results.append(
            f"{i}. {title}\n"
            f"   Channel: {channel_title}\n"
            f"   Published: {published_at}\n"
            f"   Video ID: {video_id}\n"
            f"   Description: {truncate_text(description)}\n"
        )
    
    return {"result": "\n".join(results)}
