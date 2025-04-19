"""
Tool for searching YouTube videos related to a specific Freebase topic.
"""

from typing import Any, Dict
from api_client import make_youtube_request
from utils import safe_get, truncate_text
from constants import MAX_RESULTS_LIMIT

async def search_by_topic(topic_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for YouTube videos related to a specific Freebase topic.
    
    Args:
        topic_id: The Freebase topic ID (can be a full URL or just the ID)
        max_results: Maximum number of results to return (default: 10, max: 50)
        
    Returns:
        Dict containing formatted search results or error
    """
    # Extract ID if a full URL was provided
    if topic_id.startswith("http"):
        topic_id = topic_id.split("/")[-1]
    
    # Ensure the ID has the proper format
    if not topic_id.startswith("/"):
        topic_id = "/" + topic_id
    
    params = {
        "part": "snippet",
        "topicId": topic_id,
        "maxResults": min(max_results, MAX_RESULTS_LIMIT["search"]),
        "type": "video"
    }
    
    data = await make_youtube_request("search", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": f"No videos found for topic {topic_id} or error fetching results."}
    
    results = [f"Videos related to topic {topic_id}:"]
    for i, item in enumerate(data["items"], 1):
        video_id = safe_get(item, "id", "videoId", default="Unknown")
        snippet = safe_get(item, "snippet", default={})
        title = safe_get(snippet, "title", default="Unknown")
        channel = safe_get(snippet, "channelTitle", default="Unknown")
        description = safe_get(snippet, "description", default="No description available")
        
        results.append(
            f"{i}. {title}\n"
            f"   Channel: {channel}\n"
            f"   Video ID: {video_id}\n"
            f"   Description: {truncate_text(description)}\n"
        )
    
    return {"result": "\n".join(results)}
