"""
Main entry point for the YouTube API MCP server.
"""

import sys
import signal
import time
import os
from typing import Any, Dict

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    print(f"Received signal {sig}, shutting down gracefully", file=sys.stderr)
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Initialize FastMCP server with capabilities
print(f"Starting YouTube MCP server initialization at {time.time()}", file=sys.stderr)
mcp = FastMCP(
    "youtube",
    capabilities={
        "resources": {
            "subscribe": True,
            "listChanged": True
        }
    }
)
print(f"FastMCP server initialized successfully at {time.time()}", file=sys.stderr)

# Load tools dynamically
from tools.channel_info import get_channel_info
mcp.tool()(get_channel_info)

from tools.thumbnail_analysis import analyze_thumbnail_effectiveness
mcp.tool()(analyze_thumbnail_effectiveness)

from tools.search_videos import search_videos
mcp.tool()(search_videos)

from tools.video_details import get_video_details
mcp.tool()(get_video_details)

from tools.channel_videos import list_channel_videos
mcp.tool()(list_channel_videos)

from tools.playlist_details import get_playlist_details
mcp.tool()(get_playlist_details)

from tools.video_comments import get_video_comments
mcp.tool()(get_video_comments)

from tools.topic_search import search_by_topic
mcp.tool()(search_by_topic)

from tools.channel_subscriptions import get_channel_subscriptions
mcp.tool()(get_channel_subscriptions)

from tools.video_performance import analyze_video_performance
mcp.tool()(analyze_video_performance)

from tools.live_broadcast import create_live_broadcast
mcp.tool()(create_live_broadcast)

from tools.captions import get_captions, analyze_captions
mcp.tool()(get_captions)
mcp.tool()(analyze_captions)

from tools.live_chat import get_active_live_chat_id, get_live_chat_messages, send_live_chat_message
mcp.tool()(get_active_live_chat_id)
mcp.tool()(get_live_chat_messages)
mcp.tool()(send_live_chat_message)

from tools.audience_analytics import get_audience_demographics, get_channel_analytics
mcp.tool()(get_audience_demographics)
mcp.tool()(get_channel_analytics)

try:
    from tools.lookup_channel import lookup_channel
    mcp.tool()(lookup_channel)
    print("Registered lookup_channel tool", file=sys.stderr)
except ImportError:
    print("WARNING: tools.lookup_channel module not found", file=sys.stderr)

try:
    from tools.video_upload import upload_video
    mcp.tool()(upload_video)
    print("Registered video_upload tool", file=sys.stderr)
except ImportError:
    print("WARNING: tools.video_upload module not found. Upload functionality will be disabled.", file=sys.stderr)
    # Create a dummy function to avoid errors
    async def upload_video(*args, **kwargs):
        return {"error": "Video upload functionality is not available. Module not found."}
    mcp.tool()(upload_video)

from tools.resources import (
    get_api_status, 
    get_trending_videos, 
    get_video_categories, 
    get_video_recommendations
)

# Register resource endpoints
mcp.resource("youtube://status")(get_api_status)
mcp.resource("youtube://trending")(get_trending_videos)
mcp.resource("youtube://categories")(get_video_categories)
mcp.resource("youtube://recommendations/{video_id}")(get_video_recommendations)

# Start the server function - only used when running as a script
def main():
    mcp.serve()

if __name__ == "__main__":
    main()
