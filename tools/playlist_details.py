"""
Tool for retrieving details about a YouTube playlist and its videos.
"""

from typing import Any, Dict
from api_client import make_youtube_request
from utils import safe_get
from constants import MAX_RESULTS_LIMIT

async def get_playlist_details(playlist_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Get details about a YouTube playlist and its videos.
    
    Args:
        playlist_id: The ID of the YouTube playlist
        max_results: Maximum number of videos to return (default: 10, max: 50)
        
    Returns:
        Dict containing formatted playlist information or error
    """
    # Cap max_results to API limit
    max_results = min(max_results, MAX_RESULTS_LIMIT["playlists"])
    
    # First get the playlist details
    playlist_params = {
        "part": "snippet,contentDetails",
        "id": playlist_id
    }
    
    playlist_data = await make_youtube_request("playlists", playlist_params)
    
    if "error" in playlist_data:
        return {"error": playlist_data["error"]}
    
    if "items" not in playlist_data or not playlist_data["items"]:
        return {"error": "Playlist not found or error fetching playlist information."}
    
    playlist = playlist_data["items"][0]
    playlist_snippet = safe_get(playlist, "snippet", default={})
    playlist_details = safe_get(playlist, "contentDetails", default={})
    
    # Now get the playlist items (videos)
    items_params = {
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": max_results
    }
    
    items_data = await make_youtube_request("playlistItems", items_params)
    
    if "error" in items_data:
        return {"error": items_data["error"]}
    
    # Format the playlist information
    playlist_info = (
        f"Playlist: {safe_get(playlist_snippet, 'title', default='Unknown')}\n"
        f"Channel: {safe_get(playlist_snippet, 'channelTitle', default='Unknown')}\n"
        f"Description: {safe_get(playlist_snippet, 'description', default='No description available')}\n"
        f"Video Count: {safe_get(playlist_details, 'itemCount', default='Unknown')}\n"
    )
    
    if "items" not in items_data:
        return {"result": playlist_info + "\nPlaylist found but no videos could be retrieved."}
    
    # Format the video list
    video_results = []
    result = playlist_info + "\nVideos:\n"
    
    for i, item in enumerate(items_data["items"], 1):
        snippet = safe_get(item, "snippet", default={})
        title = safe_get(snippet, "title", default="Unknown")
        position = safe_get(snippet, "position", default=i-1) + 1  # Position is 0-indexed
        video_id = safe_get(snippet, "resourceId", "videoId", default="Unknown")
        channel_title = safe_get(snippet, "videoOwnerChannelTitle", default="Unknown")
        
        video_results.append(
            f"{position}. {title}\n"
            f"   Channel: {channel_title}\n"
            f"   Video ID: {video_id}\n"
        )
    
    return {"result": result + "\n".join(video_results)}
