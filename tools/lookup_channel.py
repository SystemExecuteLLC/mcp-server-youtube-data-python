"""
Utility tool for looking up YouTube channel IDs from handles.
"""

from typing import Any, Dict, Optional
import asyncio
import os
import sys

# Import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import make_youtube_request
from utils import resolve_channel_identifier

async def lookup_channel(handle: str) -> Dict[str, Any]:
    """Look up a YouTube channel ID from a handle or username.
    
    Args:
        handle: YouTube handle, username, or channel ID
        
    Returns:
        Dict containing channel ID or error
    """
    channel_id = await resolve_channel_identifier(handle)
    
    if channel_id:
        # Get additional channel information
        params = {
            "part": "snippet,statistics",
            "id": channel_id
        }
        
        data = await make_youtube_request("channels", params)
        
        if "error" in data:
            return {"error": data["error"]}
        
        if "items" in data and data["items"]:
            channel = data["items"][0]
            snippet = channel.get("snippet", {})
            statistics = channel.get("statistics", {})
            
            result = f"""
Channel Information for "{handle}":

Channel ID: {channel_id}
Title: {snippet.get("title", "Unknown")}
Custom URL: {snippet.get("customUrl", "None")}
Description: {snippet.get("description", "")[:100]}{"..." if len(snippet.get("description", "")) > 100 else ""}
Published: {snippet.get("publishedAt", "Unknown")}
Country: {snippet.get("country", "Unknown")}

Subscriber Count: {statistics.get("subscriberCount", "Hidden")}
Video Count: {statistics.get("videoCount", "Unknown")}
View Count: {statistics.get("viewCount", "Unknown")}

Thumbnail URL: {snippet.get("thumbnails", {}).get("high", {}).get("url", "None")}
"""
            return {"result": result}
        else:
            return {"error": "Channel found but no details available."}
    else:
        return {"error": f"Could not resolve handle: {handle}. Try a different identifier."}

# Command-line interface for standalone usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lookup_channel.py [handle]")
        sys.exit(1)
        
    handle = sys.argv[1]
    result = asyncio.run(lookup_channel(handle))
    
    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)
    else:
        print(result["result"])
