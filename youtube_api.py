from typing import Any, Dict, List, Optional
import httpx
import sys
import signal
import time
import os
import json
from mcp.server.fastmcp import FastMCP

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

# Constants
YOUTUBE_API_BASE = "https://youtube.googleapis.com/youtube/v3"
USER_AGENT = "youtube-mcp-server/1.0"

from dotenv import load_dotenv
import os
import sys

# Load environment variables from .env file
load_dotenv()

# Load API key from environment
def get_api_key() -> str:
    """Get the YouTube API key from environment variables."""
    api_key = os.getenv("YOUTUBE_API_KEY")  # Use os.getenv for better readability
    if not api_key:
        print("WARNING: YOUTUBE_API_KEY environment variable not set", file=sys.stderr)
        return ""
    return api_key

async def make_youtube_request(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make a request to the YouTube API with proper error handling."""
    if params is None:
        params = {}
    
    # Add API key to params
    api_key = get_api_key()
    if not api_key:
        print("Error: YouTube API key not available", file=sys.stderr)
        print("DEBUG: Returning error as dict", file=sys.stderr)
        return {"error": "YouTube API key not available"}
    
    params["key"] = api_key
    
    url = f"{YOUTUBE_API_BASE}/{endpoint}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    
    print(f"Making request to {url} with params {params}", file=sys.stderr)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            print(f"Response status: {response.status_code}", file=sys.stderr)
            response.raise_for_status()
            try:
                json_data = response.json()
                print(f"DEBUG: Successfully parsed JSON response", file=sys.stderr)
                return json_data
            except Exception as e:
                print(f"Error parsing JSON from {url}: {str(e)}", file=sys.stderr)
                print(f"Response content: {response.text[:500]}", file=sys.stderr)  # First 500 chars to avoid huge logs
                error_dict = {"error": f"Error parsing JSON from {url}: {str(e)}"}
                print(f"DEBUG: Returning error as dict: {error_dict}", file=sys.stderr)
                return error_dict
        except httpx.HTTPStatusError as e:
            print(f"HTTP error from {url}: {e.response.status_code} {e.response.reason_phrase}", file=sys.stderr)
            error_message = f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
            try:
                print(f"Error response content: {e.response.text[:500]}", file=sys.stderr)  # First 500 chars
                # Try to parse error response as JSON
                try:
                    error_json = e.response.json()
                    if "error" in error_json and "message" in error_json["error"]:
                        error_message = error_json["error"]["message"]
                except:
                    pass
            except Exception:
                pass  # In case response text is not available
            return {"error": error_message}
        except httpx.RequestError as e:
            print(f"Request error to {url}: {str(e)}", file=sys.stderr)
            return {"error": f"Request error: {str(e)}"}
        except Exception as e:
            print(f"Unexpected error in request to {url}: {str(e)} ({type(e).__name__})", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Unexpected error: {str(e)}"}

@mcp.tool()
async def get_channel_info(channel_id: str) -> Dict[str, Any]:
    """Get information about a YouTube channel.
    
    Args:
        channel_id: The ID of the YouTube channel
    """
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": channel_id
    }
    
    data = await make_youtube_request("channels", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "Channel not found or error fetching channel information."}
    
    channel = data["items"][0]
    snippet = channel.get("snippet", {})
    statistics = channel.get("statistics", {})
    
    # Format a readable response
    result = f"""
Channel: {snippet.get('title', 'Unknown')}
Description: {snippet.get('description', 'No description available')}
Published: {snippet.get('publishedAt', 'Unknown')}
Subscriber Count: {statistics.get('subscriberCount', 'Unknown')}
Video Count: {statistics.get('videoCount', 'Unknown')}
View Count: {statistics.get('viewCount', 'Unknown')}
"""
    return {"result": result}

@mcp.tool()
async def search_videos(query: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for YouTube videos based on a query.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 10, max: 50)
    """
    # Cap max_results to 50 (YouTube API limit)
    if max_results > 50:
        max_results = 50
    
    params = {
        "part": "snippet",
        "q": query,
        "maxResults": max_results,
        "type": "video"
    }
    
    data = await make_youtube_request("search", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "No videos found or error fetching search results."}
    
    results = []
    for i, item in enumerate(data["items"], 1):
        video_id = item.get("id", {}).get("videoId", "Unknown")
        snippet = item.get("snippet", {})
        title = snippet.get("title", "Unknown")
        description = snippet.get("description", "No description available")
        channel_title = snippet.get("channelTitle", "Unknown")
        published_at = snippet.get("publishedAt", "Unknown")
        
        results.append(f"{i}. {title}\n   Channel: {channel_title}\n   Published: {published_at}\n   Video ID: {video_id}\n   Description: {description[:100]}{'...' if len(description) > 100 else ''}\n")
    
    return {"result": "\n".join(results)}

@mcp.tool()
async def get_video_details(video_id: str) -> Dict[str, Any]:
    """Get detailed information about a YouTube video.
    
    Args:
        video_id: The ID of the YouTube video
    """
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": video_id
    }
    
    data = await make_youtube_request("videos", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "Video not found or error fetching video information."}
    
    video = data["items"][0]
    snippet = video.get("snippet", {})
    statistics = video.get("statistics", {})
    content_details = video.get("contentDetails", {})
    
    # Format a readable response
    result = f"""
Video: {snippet.get('title', 'Unknown')}
Channel: {snippet.get('channelTitle', 'Unknown')}
Published: {snippet.get('publishedAt', 'Unknown')}
Duration: {content_details.get('duration', 'Unknown')}
View Count: {statistics.get('viewCount', 'Unknown')}
Like Count: {statistics.get('likeCount', 'Unknown')}
Comment Count: {statistics.get('commentCount', 'Unknown')}

Description:
{snippet.get('description', 'No description available')}
"""
    return {"result": result}

@mcp.tool()
async def list_channel_videos(channel_id: str, max_results: int = 10) -> Dict[str, Any]:
    """List videos from a specific YouTube channel.
    
    Args:
        channel_id: The ID of the YouTube channel
        max_results: Maximum number of results to return (default: 10, max: 50)
    """
    # Cap max_results to 50 (YouTube API limit)
    if max_results > 50:
        max_results = 50
    
    # First, we need to get the uploads playlist ID for the channel
    channel_params = {
        "part": "contentDetails",
        "id": channel_id
    }
    
    channel_data = await make_youtube_request("channels", channel_params)
    
    if "error" in channel_data:
        return {"error": channel_data["error"]}
    
    if "items" not in channel_data or not channel_data["items"]:
        return {"error": "Channel not found or error fetching channel information."}
    
    uploads_playlist_id = channel_data["items"][0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    
    if not uploads_playlist_id:
        return {"error": "Could not find uploads playlist for this channel."}
    
    # Now get the videos from the uploads playlist
    playlist_params = {
        "part": "snippet",
        "playlistId": uploads_playlist_id,
        "maxResults": max_results
    }
    
    playlist_data = await make_youtube_request("playlistItems", playlist_params)
    
    if "error" in playlist_data:
        return {"error": playlist_data["error"]}
    
    if "items" not in playlist_data or not playlist_data["items"]:
        return {"error": "No videos found or error fetching videos."}
    
    results = []
    for i, item in enumerate(playlist_data["items"], 1):
        snippet = item.get("snippet", {})
        title = snippet.get("title", "Unknown")
        published_at = snippet.get("publishedAt", "Unknown")
        video_id = snippet.get("resourceId", {}).get("videoId", "Unknown")
        description = snippet.get("description", "No description available")
        
        results.append(f"{i}. {title}\n   Published: {published_at}\n   Video ID: {video_id}\n   Description: {description[:100]}{'...' if len(description) > 100 else ''}\n")
    
    return {"result": "\n".join(results)}

@mcp.tool()
async def get_playlist_details(playlist_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Get details about a YouTube playlist and its videos.
    
    Args:
        playlist_id: The ID of the YouTube playlist
        max_results: Maximum number of videos to return (default: 10, max: 50)
    """
    # Cap max_results to 50 (YouTube API limit)
    if max_results > 50:
        max_results = 50
    
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
    playlist_snippet = playlist.get("snippet", {})
    playlist_details = playlist.get("contentDetails", {})
    
    # Now get the playlist items (videos)
    items_params = {
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": max_results
    }
    
    items_data = await make_youtube_request("playlistItems", items_params)
    
    if "error" in items_data:
        return {"error": items_data["error"]}
    
    if "items" not in items_data:
        playlist_info = f"Playlist found but no videos could be retrieved.\n\nPlaylist: {playlist_snippet.get('title', 'Unknown')}\nChannel: {playlist_snippet.get('channelTitle', 'Unknown')}\nDescription: {playlist_snippet.get('description', 'No description available')}\nVideo Count: {playlist_details.get('itemCount', 'Unknown')}"
        return {"result": playlist_info}
    
    # Format the playlist information
    result = f"Playlist: {playlist_snippet.get('title', 'Unknown')}\nChannel: {playlist_snippet.get('channelTitle', 'Unknown')}\nDescription: {playlist_snippet.get('description', 'No description available')}\nVideo Count: {playlist_details.get('itemCount', 'Unknown')}\n\nVideos:\n"
    
    # Format the video list
    video_results = []
    for i, item in enumerate(items_data["items"], 1):
        snippet = item.get("snippet", {})
        title = snippet.get("title", "Unknown")
        position = snippet.get("position", i-1) + 1  # Position is 0-indexed
        video_id = snippet.get("resourceId", {}).get("videoId", "Unknown")
        channel_title = snippet.get("videoOwnerChannelTitle", "Unknown")
        
        video_results.append(f"{position}. {title}\n   Channel: {channel_title}\n   Video ID: {video_id}\n")
    
    return {"result": result + "\n".join(video_results)}

@mcp.tool()
async def get_video_comments(video_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Get comments for a YouTube video.
    
    Args:
        video_id: The ID of the YouTube video
        max_results: Maximum number of comments to return (default: 10, max: 100)
    """
    # Cap max_results to 100 (reasonable limit)
    if max_results > 100:
        max_results = 100
    
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": max_results,
        "textFormat": "plainText"
    }
    
    data = await make_youtube_request("commentThreads", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "No comments found or error fetching comments."}
    
    results = [f"Comments for video {video_id}:\n"]
    for i, item in enumerate(data["items"], 1):
        comment = item.get("snippet", {}).get("topLevelComment", {})
        snippet = comment.get("snippet", {})
        
        author = snippet.get("authorDisplayName", "Anonymous")
        text = snippet.get("textDisplay", "[No comment text]")
        like_count = snippet.get("likeCount", 0)
        published_at = snippet.get("publishedAt", "Unknown")
        
        # Get reply count if available
        reply_count = item.get("snippet", {}).get("totalReplyCount", 0)
        reply_info = f" [{reply_count} replies]" if reply_count > 0 else ""
        
        results.append(f"{i}. {author} - {published_at}{reply_info}\n   Likes: {like_count}\n   {text}\n")
    
    return {"result": "\n".join(results)}

@mcp.tool()
async def search_by_topic(topic_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for YouTube videos related to a specific Freebase topic.
    
    Args:
        topic_id: The Freebase topic ID (can be a full URL or just the ID)
        max_results: Maximum number of results to return (default: 10, max: 50)
    """
    # Extract ID if a full URL was provided
    if topic_id.startswith("http"):
        topic_id = topic_id.split("/")[-1]
    
    # Ensure the ID has the proper format
    if not topic_id.startswith("/"):
        topic_id = "/" + topic_id
    
    params = {
        "part": "snippet",
        "topicId": topic_id,
        "maxResults": min(max_results, 50),
        "type": "video"
    }
    
    data = await make_youtube_request("search", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": f"No videos found for topic {topic_id} or error fetching results."}
    
    results = [f"Videos related to topic {topic_id}:"]
    for i, item in enumerate(data["items"], 1):
        video_id = item.get("id", {}).get("videoId", "Unknown")
        snippet = item.get("snippet", {})
        title = snippet.get("title", "Unknown")
        channel = snippet.get("channelTitle", "Unknown")
        description = snippet.get("description", "No description available")[:100]
        
        results.append(f"{i}. {title}\n   Channel: {channel}\n   Video ID: {video_id}\n   Description: {description}{'...' if len(snippet.get('description', '')) > 100 else ''}\n")
    
    return {"result": "\n".join(results)}

@mcp.tool()
async def get_channel_subscriptions(channel_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Get a list of channels that the specified channel is subscribed to.
    Note: This requires OAuth authorization and can only be used with the 
    channel of the authorized user, not arbitrary channels.
    
    Args:
        channel_id: The ID of the YouTube channel (must be authorized user's channel)
        max_results: Maximum number of results to return (default: 10, max: 50)
    """
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "maxResults": min(max_results, 50),
        "order": "alphabetical"
    }
    
    data = await make_youtube_request("subscriptions", params)
    
    if "error" in data:
        if isinstance(data["error"], dict) and "message" in data["error"]:
            error_message = data["error"]["message"]
        else:
            error_message = str(data["error"])
        return {"error": f"API Error: {error_message}\n\nNote: This function requires OAuth authentication and only works with the authenticated user's channel."}
    
    if "items" not in data or not data["items"]:
        return {"error": "No subscriptions found or this channel's subscriptions are private."}
    
    results = [f"Subscriptions for channel {channel_id}:"]
    for i, item in enumerate(data["items"], 1):
        snippet = item.get("snippet", {})
        title = snippet.get("title", "Unknown")
        channel_id = snippet.get("resourceId", {}).get("channelId", "Unknown")
        description = snippet.get("description", "No description")[:100]
        
        results.append(f"{i}. {title} (ID: {channel_id})\n   {description}{'...' if len(snippet.get('description', '')) > 100 else ''}")
    
    return {"result": "\n".join(results)}

@mcp.resource("youtube://status")
def get_api_status() -> Dict[str, Any]:
    """Check if the YouTube API is configured correctly."""
    print("Accessing YouTube API status resource", file=sys.stderr)
    api_key = get_api_key()
    if not api_key:
        return {"error": "YouTube API key not configured. Please set the YOUTUBE_API_KEY environment variable."}
    return {"result": "YouTube API is configured with an API key."}

@mcp.resource("youtube://trending")
async def get_trending_videos() -> Dict[str, Any]:
    """Get current trending videos on YouTube."""
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
        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})
        
        title = snippet.get("title", "Unknown")
        channel = snippet.get("channelTitle", "Unknown")
        views = statistics.get("viewCount", "Unknown")
        
        results.append(f"{i}. {title} | {channel} | {views} views")
    
    return {"result": "\n".join(results)}

@mcp.resource("youtube://categories")
async def get_video_categories() -> Dict[str, Any]:
    """Get list of YouTube video categories."""
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
        category_id = category.get("id", "Unknown")
        title = category.get("snippet", {}).get("title", "Unknown")
        
        results.append(f"{category_id}: {title}")
    
    return {"result": "\n".join(results)}

@mcp.resource("youtube://recommendations/{video_id}")
async def get_video_recommendations(video_id: str = None) -> Dict[str, Any]:
    """Get YouTube video recommendations based on a video ID or trending videos.
    
    Args:
        video_id: Optional ID of a video to get recommendations for
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
            video_id = item.get("id", {}).get("videoId", "Unknown")
            snippet = item.get("snippet", {})
        else:  # videos endpoint
            video_id = item.get("id", "Unknown")
            snippet = item.get("snippet", {})
            
        title = snippet.get("title", "Unknown")
        channel = snippet.get("channelTitle", "Unknown")
        
        results.append(f"{i}. {title} | {channel} | ID: {video_id}")
    
    return {"result": "\n".join(results)}

def log_mcp_version_info():
    """Log MCP version information for debugging."""
    try:
        import mcp
        print(f"MCP SDK version: {getattr(mcp, '__version__', 'unknown')}", file=sys.stderr)
        if hasattr(mcp, '__file__'):
            print(f"MCP location: {mcp.__file__}", file=sys.stderr)
        
        # Check if we're running under uv
        is_uv = 'UV_SUBPROCESS' in os.environ or os.environ.get('VIRTUAL_ENV', '').endswith('/.uv')
        print(f"Running under UV: {is_uv}", file=sys.stderr)
    except Exception as e:
        print(f"Error getting MCP version info: {str(e)}", file=sys.stderr)

if __name__ == "__main__":
    # Initialize and run the server
    print("Starting YouTube MCP server with stdio transport...", file=sys.stderr)
    try:
        print("Environment variables:", file=sys.stderr)
        for key, value in os.environ.items():
            if key.startswith("PYTHON") or key == "PATH" or "UV" in key or key == "YOUTUBE_API_KEY":
                # Don't print the actual API key value for security reasons
                if key == "YOUTUBE_API_KEY":
                    print(f"  {key}=***Set***", file=sys.stderr)
                else:
                    print(f"  {key}={value}", file=sys.stderr)
        
        print("Python version:", sys.version, file=sys.stderr)
        print("Python executable:", sys.executable, file=sys.stderr)
        print("Working directory:", os.getcwd(), file=sys.stderr)
        
        # Log MCP version info
        log_mcp_version_info()
        
        # Add a small delay to ensure everything is initialized
        time.sleep(0.5)
        
        # Add debug wrapper for MCP tools and resources
        print("DEBUG: Adding debug wrapper for MCP tools and resources", file=sys.stderr)
        original_tool = mcp.tool
        original_resource = mcp.resource
        
        def debug_tool_wrapper(*args, **kwargs):
            original_decorator = original_tool(*args, **kwargs)
            def wrapper(func):
                @original_decorator
                async def wrapped_func(*func_args, **func_kwargs):
                    print(f"DEBUG: Calling tool {func.__name__} with args {func_args} and kwargs {func_kwargs}", file=sys.stderr)
                    try:
                        result = await func(*func_args, **func_kwargs)
                        print(f"DEBUG: Tool {func.__name__} returned: {type(result)}", file=sys.stderr)
                        if not isinstance(result, dict):
                            print(f"WARNING: Tool {func.__name__} returned non-dict: {result}", file=sys.stderr)
                            result = {"result": str(result)}
                        return result
                    except Exception as e:
                        print(f"DEBUG: Tool {func.__name__} raised exception: {str(e)}", file=sys.stderr)
                        import traceback
                        traceback.print_exc(file=sys.stderr)
                        return {"error": f"Exception in {func.__name__}: {str(e)}"}
                return wrapped_func
            return wrapper
        
        def debug_resource_wrapper(*args, **kwargs):
            original_decorator = original_resource(*args, **kwargs)
            def wrapper(func):
                @original_decorator
                async def wrapped_func(*func_args, **func_kwargs):
                    print(f"DEBUG: Calling resource {func.__name__} with args {func_args} and kwargs {func_kwargs}", file=sys.stderr)
                    try:
                        result = await func(*func_args, **func_kwargs) if callable(getattr(func, '__await__', None)) else func(*func_args, **func_kwargs)
                        print(f"DEBUG: Resource {func.__name__} returned: {type(result)}", file=sys.stderr)
                        if not isinstance(result, dict):
                            print(f"WARNING: Resource {func.__name__} returned non-dict: {result}", file=sys.stderr)
                            result = {"result": str(result)}
                        return result
                    except Exception as e:
                        print(f"DEBUG: Resource {func.__name__} raised exception: {str(e)}", file=sys.stderr)
                        import traceback
                        traceback.print_exc(file=sys.stderr)
                        return {"error": f"Exception in {func.__name__}: {str(e)}"}
                return wrapped_func if callable(getattr(func, '__await__', None)) else wrapped_func()
            return wrapper
        
        # Replace MCP decorators with debug versions
        mcp.tool = debug_tool_wrapper
        mcp.resource = debug_resource_wrapper
        
        # Explicitly set stdio transport
        print("Attempting to start MCP run with stdio transport...", file=sys.stderr)
        mcp.run(transport='stdio')
    except Exception as e:
        print(f"Error running MCP server: {str(e)}", file=sys.stderr)
        print(f"Error type: {type(e)}", file=sys.stderr)
        if hasattr(e, "__traceback__"):
            import traceback
            traceback.print_tb(e.__traceback__, file=sys.stderr)
        sys.exit(1)
