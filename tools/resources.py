"""
Resource endpoints for the YouTube API MCP server.
"""

import sys
from typing import Any, Dict, Optional
from api_client import make_youtube_request
from utils import safe_get, get_api_key

def get_api_status() -> Dict[str, Any]:
    """Check if the YouTube API is configured correctly.
    
    Returns:
        Dict containing API status information
    """
    print("Accessing YouTube API status resource", file=sys.stderr)
    api_key = get_api_key()
    if not api_key:
        return {"error": "YouTube API key not configured. Please set the YOUTUBE_API_KEY environment variable."}
    return {"result": "YouTube API is configured with an API key."}

async def get_trending_videos() -> Dict[str, Any]:
    """Get current trending videos on YouTube.
    
    Returns:
        Dict containing formatted trending videos list or error
    """
    print("Accessing trending videos resource", file=sys.stderr)
    
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "maxResults": 10
    }
    
    data = await make_youtube_request("videos", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "Error fetching trending videos."}
    
    results = ["Current Trending Videos:"]
    for i, video in enumerate(data["items"], 1):
        snippet = safe_get(video, "snippet", default={})
        statistics = safe_get(video, "statistics", default={})
        
        title = safe_get(snippet, "title", default="Unknown")
        channel = safe_get(snippet, "channelTitle", default="Unknown")
        views = safe_get(statistics, "viewCount", default="Unknown")
        
        results.append(f"{i}. {title} | {channel} | {views} views")
    
    return {"result": "\n".join(results)}

async def get_video_categories() -> Dict[str, Any]:
    """Get list of YouTube video categories.
    
    Returns:
        Dict containing formatted category list or error
    """
    print("Accessing video categories resource", file=sys.stderr)
    
    params = {
        "part": "snippet",
        "regionCode": "US"  # Default to US categories
    }
    
    data = await make_youtube_request("videoCategories", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "Error fetching video categories."}
    
    results = ["YouTube Video Categories:"]
    for category in data["items"]:
        category_id = safe_get(category, "id", default="Unknown")
        title = safe_get(category, "snippet", "title", default="Unknown")
        
        results.append(f"{category_id}: {title}")
    
    return {"result": "\n".join(results)}

async def get_video_recommendations(video_id: str = None) -> Dict[str, Any]:
    """Get YouTube video recommendations based on a video ID or trending videos.
    
    Args:
        video_id: Optional ID of a video to get recommendations for
        
    Returns:
        Dict containing formatted recommendation list or error
    """
    print(f"Accessing recommendations resource for video_id={video_id}", file=sys.stderr)
    
    if video_id:
        # Get related videos
        params = {
            "part": "snippet",
            "relatedToVideoId": video_id,
            "type": "video",
            "maxResults": 10
        }
        
        endpoint = "search"
        title = f"Recommendations based on video {video_id}:"
    else:
        # Get trending videos
        params = {
            "part": "snippet",
            "chart": "mostPopular",
            "maxResults": 10
        }
        
        endpoint = "videos"
        title = "Recommended trending videos:"
    
    data = await make_youtube_request(endpoint, params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "Error fetching video recommendations."}
    
    results = [title]
    
    for i, item in enumerate(data["items"], 1):
        if endpoint == "search":
            video_id = safe_get(item, "id", "videoId", default="Unknown")
            snippet = safe_get(item, "snippet", default={})
        else:  # videos endpoint
            video_id = safe_get(item, "id", default="Unknown")
            snippet = safe_get(item, "snippet", default={})
            
        title = safe_get(snippet, "title", default="Unknown")
        channel = safe_get(snippet, "channelTitle", default="Unknown")
        
        results.append(f"{i}. {title} | {channel} | ID: {video_id}")
    
    return {"result": "\n".join(results)}
