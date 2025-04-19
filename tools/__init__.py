"""
Tool functions for the YouTube API MCP server.
"""

from .channel_info import get_channel_info
from .thumbnail_analysis import analyze_thumbnail_effectiveness
from .search_videos import search_videos
from .video_details import get_video_details
from .channel_videos import list_channel_videos
from .playlist_details import get_playlist_details
from .video_comments import get_video_comments
from .topic_search import search_by_topic
from .channel_subscriptions import get_channel_subscriptions
from .video_performance import analyze_video_performance
from .live_broadcast import create_live_broadcast
from .captions import get_captions, analyze_captions
from .live_chat import get_active_live_chat_id, get_live_chat_messages, send_live_chat_message
from .audience_analytics import get_audience_demographics, get_channel_analytics
from .video_upload import upload_video
from .resources import (
    get_api_status, 
    get_trending_videos, 
    get_video_categories, 
    get_video_recommendations
)

__all__ = [
    'get_channel_info',
    'analyze_thumbnail_effectiveness',
    'search_videos',
    'get_video_details',
    'list_channel_videos',
    'get_playlist_details',
    'get_video_comments',
    'search_by_topic',
    'get_channel_subscriptions',
    'analyze_video_performance',
    'create_live_broadcast',
    'get_captions',
    'analyze_captions',
    'get_active_live_chat_id',
    'get_live_chat_messages',
    'send_live_chat_message',
    'get_audience_demographics',
    'get_channel_analytics',
    'upload_video',
    'get_api_status',
    'get_trending_videos',
    'get_video_categories',
    'get_video_recommendations',
]
