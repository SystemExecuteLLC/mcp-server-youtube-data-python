"""
Tool for retrieving comments from a YouTube video.
"""

from typing import Any, Dict
from api_client import make_youtube_request
from utils import safe_get
from constants import MAX_RESULTS_LIMIT

async def get_video_comments(video_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Get comments for a YouTube video.
    
    Args:
        video_id: The ID of the YouTube video
        max_results: Maximum number of comments to return (default: 10, max: 100)
        
    Returns:
        Dict containing formatted comment list or error
    """
    # Cap max_results to limit
    max_results = min(max_results, MAX_RESULTS_LIMIT["comments"])
    
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": max_results,
        "textFormat": "plainText"
    }
    
    data = await make_youtube_request("commentThreads", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "No comments found or error fetching comments."}
    
    results = [f"Comments for video {video_id}:\n"]
    for i, item in enumerate(data["items"], 1):
        comment = safe_get(item, "snippet", "topLevelComment", default={})
        snippet = safe_get(comment, "snippet", default={})
        
        author = safe_get(snippet, "authorDisplayName", default="Anonymous")
        text = safe_get(snippet, "textDisplay", default="[No comment text]")
        like_count = safe_get(snippet, "likeCount", default=0)
        published_at = safe_get(snippet, "publishedAt", default="Unknown")
        
        # Get reply count if available
        reply_count = safe_get(item, "snippet", "totalReplyCount", default=0)
        reply_info = f" [{reply_count} replies]" if reply_count > 0 else ""
        
        results.append(
            f"{i}. {author} - {published_at}{reply_info}\n"
            f"   Likes: {like_count}\n"
            f"   {text}\n"
        )
    
    # Include pagination token if available
    if "nextPageToken" in data:
        results.append(f"\nNext page token: {data['nextPageToken']}")
    
    return {"result": "\n".join(results)}
