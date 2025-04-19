"""
Tools for interacting with YouTube live chat.
"""

import os
import sys
from typing import Any, Dict, List, Optional

from api_client import make_youtube_request, make_youtube_post_request, get_oauth_credentials
from utils import safe_get
from constants import MAX_RESULTS_LIMIT, YOUTUBE_API_BASE, USER_AGENT

async def get_active_live_chat_id(video_id: str) -> Dict[str, Any]:
    """Get the active live chat ID for a YouTube livestream.
    
    This utility function retrieves the live chat ID for a currently active livestream,
    which is required for both retrieving and sending chat messages.
    
    Args:
        video_id: The ID of the YouTube livestream video
        
    Returns:
        Dict containing live chat ID or error
    """
    params = {
        "part": "liveStreamingDetails",
        "id": video_id
    }
    
    data = await make_youtube_request("videos", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "Video not found or error fetching video information."}
    
    video = data["items"][0]
    streaming_details = safe_get(video, "liveStreamingDetails", default={})
    live_chat_id = safe_get(streaming_details, "activeLiveChatId")
    
    if not live_chat_id:
        return {
            "error": "No active live chat found for this video. "
                    "It may not be a livestream or the livestream may have ended."
        }
    
    return {
        "result": (
            f"Active Live Chat ID: {live_chat_id}\n\n"
            "Use this ID with get_live_chat_messages or send_live_chat_message functions."
        )
    }

async def get_live_chat_messages(live_chat_id: str, max_results: int = 20) -> Dict[str, Any]:
    """Get live chat messages from a YouTube livestream.
    
    This function retrieves messages from a live chat by its ID. The live chat ID can be obtained
    from the video details of a livestream using the get_video_details function.
    
    Args:
        live_chat_id: The ID of the live chat to retrieve messages from
        max_results: Maximum number of messages to return (default: 20, max: 200)
        
    Returns:
        Dict containing formatted chat messages or error
    """
    # Cap max_results to limit
    max_results = min(max_results, MAX_RESULTS_LIMIT["live_chat"])
    
    params = {
        "part": "snippet,authorDetails",
        "liveChatId": live_chat_id,
        "maxResults": max_results
    }
    
    data = await make_youtube_request("liveChat/messages", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "No chat messages found or error fetching messages."}
    
    # Format the results
    results = [f"Live Chat Messages (ID: {live_chat_id}):"]
    
    for item in data["items"]:
        snippet = safe_get(item, "snippet", default={})
        author_details = safe_get(item, "authorDetails", default={})
        
        # Get message content
        message_type = safe_get(snippet, "type", default="Unknown")
        display_message = safe_get(snippet, "displayMessage", default="[No message content]")
        published_at = safe_get(snippet, "publishedAt", default="Unknown")
        
        # Get author information
        author_name = safe_get(author_details, "displayName", default="Anonymous")
        author_channel_id = safe_get(author_details, "channelId", default="Unknown")
        is_verified = safe_get(author_details, "isVerified", default=False)
        is_chat_owner = safe_get(author_details, "isChatOwner", default=False)
        is_chat_sponsor = safe_get(author_details, "isChatSponsor", default=False)
        is_chat_moderator = safe_get(author_details, "isChatModerator", default=False)
        
        # Create author badges for special roles
        badges = []
        if is_chat_owner:
            badges.append("OWNER")
        if is_chat_moderator:
            badges.append("MOD")
        if is_chat_sponsor:
            badges.append("SPONSOR")
        if is_verified:
            badges.append("VERIFIED")
        
        badge_str = f" [{', '.join(badges)}]" if badges else ""
        
        # Format the message
        results.append(f"{author_name}{badge_str} ({published_at}): {display_message}")
    
    # Include pagination token if available
    if "nextPageToken" in data:
        results.append(f"\nNext page token: {data['nextPageToken']}")
    
    return {"result": "\n".join(results)}

async def send_live_chat_message(live_chat_id: str, message_text: str) -> Dict[str, Any]:
    """Send a message to a YouTube livestream chat.
    
    This function posts a message to a live chat by its ID. The sender must be authorized
    via OAuth and have permission to send messages in the specified chat.
    
    Args:
        live_chat_id: The ID of the live chat to send a message to
        message_text: The text content of the message to send
        
    Returns:
        Dict containing message send status or error
    """
    # Validate input parameters
    if not live_chat_id:
        return {"error": "Live chat ID is required."}
        
    if not message_text or len(message_text.strip()) == 0:
        return {"error": "Message text cannot be empty."}
    
    # Get OAuth token
    oauth_token = await get_oauth_credentials()
    if not oauth_token:
        return {
            "error": "OAuth credentials not available. Set YOUTUBE_OAUTH_TOKEN environment variable"
        }
    
    # Set up the API request payload
    message_data = {
        "snippet": {
            "liveChatId": live_chat_id,
            "type": "textMessageEvent",
            "textMessageDetails": {
                "messageText": message_text
            }
        }
    }
    
    # Make the API request
    result = await make_youtube_post_request(
        endpoint="liveChat/messages", 
        data=message_data,
        params={"part": "snippet"},
        oauth_token=oauth_token
    )
    
    # Check if the message was successfully posted
    if "error" in result:
        return {"error": f"Failed to send message: {result['error']}"}
        
    if "id" in result:
        message_id = result["id"]
        snippet = safe_get(result, "snippet", default={})
        author = safe_get(snippet, "authorDisplayName", default="You")
        message = safe_get(snippet, "displayMessage", default=message_text)
        
        return {
            "result": (
                f"Message successfully sent to live chat!\n\n"
                f"Message ID: {message_id}\n"
                f"Author: {author}\n"
                f"Content: {message}"
            )
        }
    else:
        return {"error": "Failed to send message. API did not return a message ID."}
