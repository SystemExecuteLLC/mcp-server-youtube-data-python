"""
Utility functions for the YouTube API MCP server.
"""

import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

def get_api_key() -> str:
    """Get the YouTube API key from environment variables.
    
    Returns:
        str: The API key or empty string if not found
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("WARNING: YOUTUBE_API_KEY environment variable not set", file=sys.stderr)
        return ""
    return api_key

def parse_srt_captions(srt_content: str) -> List[Dict[str, Any]]:
    """Parse SRT format captions into structured data.
    
    Args:
        srt_content: String containing SRT format caption data
        
    Returns:
        List of caption entries with timing and text information
    """
    import re
    
    # Regular expression to parse SRT format
    pattern = re.compile(r'(\d+)\s+(\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2},\d{3})\s+(.+?)(?=\n\n\d+\s+|\Z)', re.DOTALL)
    
    entries = []
    matches = pattern.findall(srt_content)
    
    for match in matches:
        index = int(match[0])
        start_time_str = match[1]
        end_time_str = match[2]
        text = match[3].strip()
        
        # Convert time strings to seconds
        def time_to_seconds(time_str):
            h, m, rest = time_str.split(':')
            s, ms = rest.split(',')
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
        
        start_seconds = time_to_seconds(start_time_str)
        end_seconds = time_to_seconds(end_time_str)
        
        entries.append({
            "index": index,
            "start_time": start_time_str,
            "end_time": end_time_str,
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
            "duration": end_seconds - start_seconds,
            "text": text
        })
    
    return entries

def format_iso_timestamp(timestamp: str) -> str:
    """Format ISO timestamp for better readability.
    
    Args:
        timestamp: ISO 8601 timestamp
    
    Returns:
        Formatted timestamp
    """
    try:
        # Remove Z and add timezone if needed
        if timestamp.endswith('Z'):
            timestamp = timestamp[:-1] + "+00:00"
        # Parse the timestamp
        dt = datetime.fromisoformat(timestamp)
        # Format in a human-readable form
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return timestamp  # Return original if parsing fails

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to a specified length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def get_date_range(days_ago: int = 30) -> tuple:
    """Get ISO formatted date range from now to specified days ago.
    
    Args:
        days_ago: Number of days in the past
    
    Returns:
        Tuple of (start_date, end_date) in ISO format
    """
    today = datetime.now()
    past = today - timedelta(days=days_ago)
    
    return (
        past.strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d")
    )

def format_number(num: int) -> str:
    """Format large numbers with commas.
    
    Args:
        num: Number to format
    
    Returns:
        Formatted number string
    """
    return f"{num:,}"

def safe_get(obj: Dict[str, Any], *keys, default: Any = None) -> Any:
    """Safely access nested dictionary keys.
    
    Args:
        obj: Dictionary to access
        keys: Sequence of keys to access
        default: Default value if keys don't exist
    
    Returns:
        Value at the nested key path or default value
    """
    current = obj
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


async def resolve_channel_identifier(channel_identifier: str) -> Optional[str]:
    """Resolve a channel identifier to a channel ID.
    
    This function accepts a channel identifier which can be a channel ID,
    a custom handle (with or without @ prefix), or a legacy username,
    and resolves it to a proper channel ID.
    
    Args:
        channel_identifier: Channel ID, handle, or username
        
    Returns:
        Channel ID if found, None if not resolvable
    """
    from api_client import make_youtube_request
    
    # If it's already a channel ID (starts with UC), return it directly
    if channel_identifier.startswith("UC"):
        return channel_identifier
        
    # For handles, make sure the @ is included
    if not channel_identifier.startswith("@") and not channel_identifier.startswith("UC"):
        channel_identifier = f"@{channel_identifier}"
    
    # Method 1: Direct API lookup using forHandle parameter
    print(f"Method 1: Trying forHandle with {channel_identifier}", file=sys.stderr)
    handle_params = {
        "part": "id",
        "forHandle": channel_identifier
    }
    handle_data = await make_youtube_request("channels", handle_params)
    if handle_data.get("items") and len(handle_data["items"]) > 0:
        channel_id = handle_data["items"][0]["id"]
        print(f"Found channel ID via forHandle: {channel_id}", file=sys.stderr)
        return channel_id
        
    # Method 2: Try forUsername parameter
    print(f"Method 2: Trying forUsername with {channel_identifier.lstrip('@')}", file=sys.stderr)
    username_params = {
        "part": "id",
        "forUsername": channel_identifier.lstrip('@')
    }
    username_data = await make_youtube_request("channels", username_params)
    if username_data.get("items") and len(username_data["items"]) > 0:
        channel_id = username_data["items"][0]["id"]
        print(f"Found channel ID via forUsername: {channel_id}", file=sys.stderr)
        return channel_id

    # Method 3: As a last resort, try search
    print(f"Method 3: Trying search with {channel_identifier}", file=sys.stderr)
    search_params = {
        "part": "snippet",
        "q": channel_identifier,
        "type": "channel",
        "maxResults": 1
    }
    
    search_data = await make_youtube_request("search", search_params)
    if search_data.get("items") and len(search_data["items"]) > 0:
        channel_id = search_data["items"][0]["snippet"].get("channelId")
        if channel_id:
            print(f"Found channel ID via search: {channel_id}", file=sys.stderr)
            return channel_id
        
    # If all methods fail, print debug info and return None
    print(f"Could not resolve channel identifier {channel_identifier} by any method", file=sys.stderr)
    return None
