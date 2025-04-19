"""
Tool for creating and scheduling YouTube live broadcasts.
"""

import httpx
import os
import sys
from typing import Any, Dict, Optional
from datetime import datetime

from api_client import get_oauth_credentials
from utils import get_api_key, safe_get
from constants import YOUTUBE_API_BASE, USER_AGENT

async def create_live_broadcast(
    title: str, 
    description: str, 
    scheduled_start_time: str, 
    privacy_status: str = "private", 
    enable_dvr: bool = True, 
    enable_auto_start: bool = True, 
    enable_auto_stop: bool = True
) -> Dict[str, Any]:
    """Create and schedule a YouTube live broadcast.
    
    This function creates a new live broadcast (livestream) on YouTube, making it easy to schedule
    upcoming streams programmatically. It handles both the broadcast and stream components required
    for a complete live streaming setup.
    
    Args:
        title: Title of the live broadcast (required)
        description: Description of the live broadcast (required)
        scheduled_start_time: ISO 8601 timestamp (YYYY-MM-DDThh:mm:ss.sssZ) for the scheduled start (required)
        privacy_status: Privacy status - 'private', 'public', or 'unlisted' (default: 'private')
        enable_dvr: Whether viewers can rewind the stream (default: True)
        enable_auto_start: Whether the broadcast should automatically start when streaming begins (default: True)
        enable_auto_stop: Whether the broadcast should automatically end when streaming stops (default: True)
    
    Returns:
        Dict containing broadcast setup details or error
    """
    # Validate input parameters
    if not title or not description or not scheduled_start_time:
        return {"error": "Title, description, and scheduled_start_time are required."}
    
    if privacy_status not in ["private", "public", "unlisted"]:
        return {"error": "Privacy status must be 'private', 'public', or 'unlisted'."}
    
    # Validate the timestamp format
    try:
        # Strip Z and add timezone information if needed
        if scheduled_start_time.endswith('Z'):
            scheduled_start_time = scheduled_start_time[:-1] + "+00:00"
        # Attempt to parse the time
        datetime.fromisoformat(scheduled_start_time)
    except ValueError:
        return {"error": "Invalid scheduled_start_time format. Use ISO 8601 format (YYYY-MM-DDThh:mm:ss.sssZ)"}
    
    # Get API key and OAuth token
    api_key = get_api_key()
    if not api_key:
        return {"error": "YouTube API key not available"}
        
    oauth_token = await get_oauth_credentials()
    if not oauth_token:
        return {"error": "OAuth credentials not available. Set YOUTUBE_OAUTH_TOKEN environment variable"}
    
    # Prepare authentication headers
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth_token}"
    }
    
    # Step 1: Create the live broadcast
    broadcast_params = {
        "part": "snippet,status,contentDetails",
        "key": api_key
    }
    
    broadcast_data = {
        "snippet": {
            "title": title,
            "description": description,
            "scheduledStartTime": scheduled_start_time
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        },
        "contentDetails": {
            "enableDvr": enable_dvr,
            "enableAutoStart": enable_auto_start,
            "enableAutoStop": enable_auto_stop
        }
    }
    
    url = f"{YOUTUBE_API_BASE}/liveBroadcasts"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url, 
                headers=headers, 
                params=broadcast_params, 
                json=broadcast_data,
                timeout=30.0
            )
            response.raise_for_status()
            broadcast_result = response.json()
            
            if "id" not in broadcast_result:
                return {"error": "Failed to create broadcast. API did not return a broadcast ID."}
            
            broadcast_id = broadcast_result["id"]
            
            # Step 2: Create the live stream (this will generate stream keys, etc.)
            stream_params = {
                "part": "snippet,cdn,contentDetails",
                "key": api_key
            }
            
            stream_data = {
                "snippet": {
                    "title": title
                },
                "cdn": {
                    "frameRate": "variable",
                    "ingestionType": "rtmp",
                    "resolution": "variable"
                },
                "contentDetails": {
                    "isReusable": True
                }
            }
            
            stream_url = f"{YOUTUBE_API_BASE}/liveStreams"
            
            stream_response = await client.post(
                stream_url, 
                headers=headers, 
                params=stream_params, 
                json=stream_data,
                timeout=30.0
            )
            stream_response.raise_for_status()
            stream_result = stream_response.json()
            
            if "id" not in stream_result:
                return {"error": "Failed to create stream. API did not return a stream ID."}
            
            stream_id = stream_result["id"]
            
            # Step 3: Bind the broadcast to the stream
            bind_params = {
                "part": "id,contentDetails",
                "id": broadcast_id,
                "streamId": stream_id,
                "key": api_key
            }
            
            bind_url = f"{YOUTUBE_API_BASE}/liveBroadcasts/bind"
            
            bind_response = await client.post(
                bind_url, 
                headers=headers, 
                params=bind_params,
                timeout=30.0
            )
            bind_response.raise_for_status()
            
            # Extract important information for the response
            stream_key = safe_get(
                stream_result, "cdn", "ingestionInfo", "streamName", 
                default="Unknown"
            )
            ingestion_address = safe_get(
                stream_result, "cdn", "ingestionInfo", "ingestionAddress", 
                default="Unknown"
            )
            playback_url = f"https://www.youtube.com/watch?v={broadcast_id}"
            
            result = f"""Successfully created live broadcast!

Broadcast Details:
Title: {title}
Description: {description}
Scheduled Start: {scheduled_start_time}
Privacy Status: {privacy_status}

Stream Information:
Broadcast ID: {broadcast_id}
Stream ID: {stream_id}
Stream Key: {stream_key}
Ingestion Address: {ingestion_address}

Playback URL: {playback_url}

Instructions:
1. Configure your streaming software (OBS, Streamlabs, etc.) with the above ingestion address and stream key
2. Start streaming to this endpoint at the scheduled time
3. The broadcast will automatically start when your stream begins (if auto-start is enabled)

Note: Keep your stream key private. Anyone with this key can stream to your channel.
"""
            
            return {"result": result}
            
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
            try:
                error_json = e.response.json()
                if "error" in error_json and "message" in error_json["error"]:
                    error_message = error_json["error"]["message"]
            except:
                pass
                
            return {"error": f"Failed to create live broadcast: {error_message}"}
            
        except Exception as e:
            return {"error": f"Unexpected error creating live broadcast: {str(e)}"}
