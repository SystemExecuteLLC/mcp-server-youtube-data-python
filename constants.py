"""
Constants for the YouTube API MCP server.
"""

# API Configuration
YOUTUBE_API_BASE = "https://youtube.googleapis.com/youtube/v3"
USER_AGENT = "youtube-mcp-server/1.0"

# Common Category IDs
CATEGORY_IDS = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "20": "Gaming",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology"
}

# YouTube API Limits
MAX_RESULTS_LIMIT = {
    "search": 50,
    "comments": 100,
    "playlists": 50,
    "videos": 50,
    "live_chat": 200
}

# Default values
DEFAULT_MAX_RESULTS = 10
DEFAULT_LANGUAGE = "en"
DEFAULT_PRIVACY_STATUS = "private"
DEFAULT_CATEGORY_ID = "22"  # People & Blogs
