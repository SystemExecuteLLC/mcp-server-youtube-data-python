"""
Tool for retrieving YouTube channel information.
"""

from typing import Any, Dict
import sys
from api_client import make_youtube_request
from utils import safe_get, resolve_channel_identifier

async def get_channel_info(channel_input: str) -> Dict[str, Any]:
    """Get information about a YouTube channel.
    
    Args:
        channel_input: The ID or handle of the YouTube channel
        
    Returns:
        Dict containing formatted channel information or error
    """
    # Print the raw input for debugging
    print(f"\n--- Debug: get_channel_info called with: '{channel_input}' ---", file=sys.stderr)
    
    # 1. First try direct channel lookup if it looks like a channel ID
    if channel_input.startswith("UC"):
        print(f"Using direct channel ID: {channel_input}", file=sys.stderr)
        channel_id = channel_input
    else:
        # 2. Otherwise, try to resolve handle/username to channel ID
        print(f"Resolving identifier: {channel_input}", file=sys.stderr)
        channel_id = await resolve_channel_identifier(channel_input)
        
    # 3. If we still don't have a channel ID, return error
    if not channel_id:
        print(f"Failed to resolve channel identifier: {channel_input}", file=sys.stderr)
        return {"error": f"Could not resolve channel identifier: {channel_input}. Please provide a valid channel ID or handle."}
    
    # 4. Now that we have a channel ID, get the channel info
    print(f"Fetching channel info for ID: {channel_id}", file=sys.stderr)
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": channel_id
    }
    
    # 5. Make the API request
    data = await make_youtube_request("channels", params)
    print(f"API response status: {'success' if 'items' in data and data.get('items') else 'failure'}", file=sys.stderr)
    
    # 6. Handle API errors
    if "error" in data:
        error_msg = data["error"]
        print(f"API error: {error_msg}", file=sys.stderr)
        return {"error": f"API error: {error_msg}"}
    
    # 7. Check if we got valid results
    if "items" not in data or not data["items"]:
        print(f"No channel data returned for ID: {channel_id}", file=sys.stderr)
        return {"error": f"Channel not found for ID: {channel_id}"}
    
    # 8. Format the results
    channel = data["items"][0]
    snippet = safe_get(channel, "snippet", default={})
    statistics = safe_get(channel, "statistics", default={})
    
    # 9. Return formatted result
    result = f"""
    Channel: {safe_get(snippet, "title", default="Unknown")}
    Description: {safe_get(snippet, "description", default="No description available")}
    Published: {safe_get(snippet, "publishedAt", default="Unknown")}
    Subscriber Count: {safe_get(statistics, "subscriberCount", default="Unknown")}
    Video Count: {safe_get(statistics, "videoCount", default="Unknown")}
    View Count: {safe_get(statistics, "viewCount", default="Unknown")}
    """
    
    print(f"Successfully retrieved channel info for: {safe_get(snippet, 'title', default='Unknown')}", file=sys.stderr)
    return {"result": result}
