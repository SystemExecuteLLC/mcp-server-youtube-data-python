"""
Tool for retrieving detailed information about a YouTube video.
"""

from typing import Any, Dict
from api_client import make_youtube_request
from utils import safe_get

async def get_video_details(video_id: str) -> Dict[str, Any]:
    """Get detailed information about a YouTube video.
    
    Args:
        video_id: The ID of the YouTube video
        
    Returns:
        Dict containing formatted video information or error
    """
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": video_id
    }
    
    data = await make_youtube_request("videos", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "Video not found or error fetching video information."}
    
    video = data["items"][0]
    snippet = safe_get(video, "snippet", default={})
    statistics = safe_get(video, "statistics", default={})
    content_details = safe_get(video, "contentDetails", default={})
    
    # Format a readable response
    result = f"""
Video: {safe_get(snippet, "title", default="Unknown")}
Channel: {safe_get(snippet, "channelTitle", default="Unknown")}
Published: {safe_get(snippet, "publishedAt", default="Unknown")}
Duration: {safe_get(content_details, "duration", default="Unknown")}
View Count: {safe_get(statistics, "viewCount", default="Unknown")}
Like Count: {safe_get(statistics, "likeCount", default="Unknown")}
Comment Count: {safe_get(statistics, "commentCount", default="Unknown")}

Description:
{safe_get(snippet, "description", default="No description available")}
"""
    return {"result": result}
