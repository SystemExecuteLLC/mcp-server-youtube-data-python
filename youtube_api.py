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
async def analyze_thumbnail_effectiveness(video_id: str, num_comparisons: int = 5, category_id: str = None) -> Dict[str, Any]:
    """Analyze thumbnail effectiveness for a YouTube video by comparing with similar high-performing videos.
    
    This function compares a video's thumbnail against thumbnails from similar successful videos,
    providing insights that can help creators optimize their thumbnails for better click-through rates.
    
    Args:
        video_id: The ID of the YouTube video to analyze
        num_comparisons: Number of similar videos to compare (default: 5, max: 10)
        category_id: Optional category ID to filter comparison videos (default: None, uses the video's category)
    """
    
    # Cap num_comparisons to 10 (reasonable limit)
    if num_comparisons > 10:
        num_comparisons = 10
    
    # Get additional video details for more context
    detailed_video_params = {
        "part": "snippet,statistics,contentDetails",
        "id": video_id
    }
    
    video_data = await make_youtube_request("videos", detailed_video_params)
    
    if "error" in video_data:
        return {"error": video_data["error"]}
    
    if "items" not in video_data or not video_data["items"]:
        return {"error": "Video not found or error fetching video information."}
    
    # Extract source video information
    source_video = video_data["items"][0]
    snippet = source_video.get("snippet", {})
    statistics = source_video.get("statistics", {})
    content_details = source_video.get("contentDetails", {})
    
    source_title = snippet.get("title", "Unknown")
    source_description = snippet.get("description", "")
    source_channel_id = snippet.get("channelId", "")
    source_channel_title = snippet.get("channelTitle", "Unknown")
    source_tags = snippet.get("tags", [])
    source_view_count = int(statistics.get("viewCount", 0))
    source_like_count = int(statistics.get("likeCount", 0))
    source_comment_count = int(statistics.get("commentCount", 0))
    source_duration = content_details.get("duration", "Unknown")
    
    # Get or use provided category ID
    if category_id is None:
        category_id = snippet.get("categoryId", "")
    
    # Extract thumbnail URLs
    source_thumbnails = snippet.get("thumbnails", {})
    source_thumbnail_url = source_thumbnails.get("maxres", {}).get("url", 
                           source_thumbnails.get("high", {}).get("url", 
                           source_thumbnails.get("default", {}).get("url", "None")))
    
    # Step 2: Get channel details for engagement context
    channel_params = {
        "part": "statistics",
        "id": source_channel_id
    }
    
    channel_data = await make_youtube_request("channels", channel_params)
    
    source_subscriber_count = 0
    if "items" in channel_data and channel_data["items"]:
        channel = channel_data["items"][0]
        source_subscriber_count = int(channel.get("statistics", {}).get("subscriberCount", 0))
    
    # Calculate engagement metrics for source video
    source_ctr_estimate = 0
    if source_subscriber_count > 0:
        # Very rough estimate based on view-to-subscriber ratio
        source_ctr_estimate = (source_view_count / source_subscriber_count) * 100
        if source_ctr_estimate > 100:
            source_ctr_estimate = 100  # Cap at 100%
    
    source_engagement_rate = 0
    if source_view_count > 0:
        source_engagement_rate = (source_like_count / source_view_count) * 100
    
    # Step 3: Find similar videos to compare
    # Extract keywords from title and tags to create a search query
    import re
    
    # Simple keyword extraction by removing common words
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
                 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                 'to', 'from', 'by', 'for', 'with', 'about', 'against', 'between',
                 'into', 'during', 'before', 'after', 'above', 'below', 'at', 'in',
                 'on', 'of', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
                 'she', 'it', 'we', 'they', 'how', 'what', 'why', 'when', 'where'}
    
    # Extract keywords from title
    title_keywords = []
    for word in re.findall(r'\b\w+\b', source_title.lower()):
        if word not in stop_words and len(word) > 2:
            title_keywords.append(word)
    
    # Combine with tags (up to 3) for better results
    search_keywords = title_keywords[:3]
    if source_tags:
        for tag in source_tags[:2]:  # Add up to 2 tags
            # Extract first word from tag if tag is a phrase
            tag_word = re.findall(r'\b\w+\b', tag.lower())
            if tag_word and tag_word[0] not in search_keywords and tag_word[0] not in stop_words:
                search_keywords.append(tag_word[0])
    
    search_query = " ".join(search_keywords)
    
    # If we couldn't extract meaningful keywords, use a portion of the title
    if not search_query and source_title:
        search_query = re.sub(r'[^\w\s]', '', source_title)[:30]
    
    # Search for similar videos
    search_params = {
        "part": "snippet",
        "q": search_query,
        "type": "video",
        "maxResults": num_comparisons + 5,  # Request more to filter out same channel
        "videoCategoryId": category_id if category_id else None,
        "videoCaption": "any",
        "order": "viewCount"  # Sort by view count to get successful videos
    }
    
    # Remove None values from params
    search_params = {k: v for k, v in search_params.items() if v is not None}
    
    search_data = await make_youtube_request("search", search_params)
    
    if "error" in search_data:
        return {"error": f"Error finding similar videos: {search_data['error']}"}
    
    if "items" not in search_data or not search_data["items"]:
        return {"error": "No similar videos found for comparison."}
    
    # Filter out videos from the same channel and the source video itself
    comparison_videos = []
    for item in search_data["items"]:
        video_id_from_search = item.get("id", {}).get("videoId", "")
        channel_id_from_search = item.get("snippet", {}).get("channelId", "")
        
        if video_id_from_search != video_id and channel_id_from_search != source_channel_id:
            comparison_videos.append(item)
            
            if len(comparison_videos) >= num_comparisons:
                break
    
    if not comparison_videos:
        return {"error": "Could not find suitable comparison videos."}
    
    # Get detailed information for comparison videos
    comparison_video_ids = [v.get("id", {}).get("videoId", "") for v in comparison_videos]
    
    # Get details for comparison videos 'contentDetails,statistics' adds duration, definition and comment counts
    detailed_video_params = {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(comparison_video_ids)
    }
    
    detailed_videos_data = await make_youtube_request("videos", detailed_video_params)
    
    if "error" in detailed_videos_data:
        return {"error": f"Error fetching comparison video details: {detailed_videos_data['error']}"}
    
    if "items" not in detailed_videos_data or not detailed_videos_data["items"]:
        return {"error": "Error retrieving detailed information for comparison videos."}
    
    # Process comparison videos data
    detailed_comparisons = []
    for item in detailed_videos_data["items"]:
        comp_snippet = item.get("snippet", {})
        comp_statistics = item.get("statistics", {})
        comp_content_details = item.get("contentDetails", {})
        
        # Get thumbnail URLs
        comp_thumbnails = comp_snippet.get("thumbnails", {})
        comp_thumbnail_url = comp_thumbnails.get("maxres", {}).get("url", 
                            comp_thumbnails.get("high", {}).get("url", 
                            comp_thumbnails.get("default", {}).get("url", "None")))
        
        # Get publish date for time-based metrics
        published_at = comp_snippet.get("publishedAt", "")
        
        # Get other detailed info
        video_duration = comp_content_details.get("duration", "Unknown")
        video_definition = comp_content_details.get("definition", "Unknown").upper()
        comment_count = int(comp_statistics.get("commentCount", 0))
        description = comp_snippet.get("description", "")[:100] + "..." if len(comp_snippet.get("description", "")) > 100 else comp_snippet.get("description", "")
        
        # Extract category name if available
        category_id = comp_snippet.get("categoryId", "")
        
        # Video details
        comparison = {
            "id": item.get("id", ""),
            "title": comp_snippet.get("title", "Unknown"),
            "channel": comp_snippet.get("channelTitle", "Unknown"),
            "thumbnail_url": comp_thumbnail_url,
            "published_at": published_at,
            "duration": video_duration,
            "definition": video_definition,
            "description": description,
            "category_id": category_id,
            "view_count": int(comp_statistics.get("viewCount", 0)),
            "like_count": int(comp_statistics.get("likeCount", 0)),
            "comment_count": comment_count
        }
        # Calculate engagement rate
        if comparison["view_count"] > 0:
            comparison["engagement_rate"] = (comparison["like_count"] / comparison["view_count"]) * 100
        else:
            comparison["engagement_rate"] = 0
            
        # Calculate time-based metrics
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc)
        
        
        try:
            # Remove the 'Z' from ISO format if present and add timezone info
            if published_at.endswith('Z'):
                published_at = published_at[:-1]
            pub_time = datetime.fromisoformat(published_at).replace(tzinfo=timezone.utc)
            days_online = (current_time - pub_time).days
            
            # Avoid division by zero
            if days_online > 0:
                comparison["days_online"] = days_online
                comparison["views_per_day"] = comparison["view_count"] / days_online
                comparison["likes_per_day"] = comparison["like_count"] / days_online
            else:
                # For videos published today
                comparison["days_online"] = 1
                comparison["views_per_day"] = comparison["view_count"]
                comparison["likes_per_day"] = comparison["like_count"]
        except (ValueError, TypeError):
            # If date parsing fails, set defaults
            comparison["days_online"] = 0
            comparison["views_per_day"] = 0
            comparison["likes_per_day"] = 0
            
        detailed_comparisons.append(comparison)
    
    # Sort comparisons by views per day (to account for video age)
    detailed_comparisons.sort(key=lambda x: x.get("views_per_day", 0), reverse=True)
    
    # Step 5: Format the analysis results
    result = f"Thumbnail Effectiveness Analysis for '{source_title}' by {source_channel_title}\n\n"
    
    # Add time-based metrics for source video
    from datetime import datetime, timezone
    current_time = datetime.now(timezone.utc)
    
    source_published_at = snippet.get("publishedAt", "")
    source_days_online = 0
    source_views_per_day = 0
    
    try:
        # Remove the 'Z' from ISO format if present and add timezone info
        if source_published_at.endswith('Z'):
            source_published_at = source_published_at[:-1]
        pub_time = datetime.fromisoformat(source_published_at).replace(tzinfo=timezone.utc)
        source_days_online = max(1, (current_time - pub_time).days)  # Avoid division by zero
        source_views_per_day = source_view_count / source_days_online
    except (ValueError, TypeError):
        # If date parsing fails, set reasonable defaults
        source_days_online = 1
        source_views_per_day = source_view_count
    
    # Source video stats with enhanced information
    result += "YOUR VIDEO:\n"
    result += f"Title: {source_title}\n"
    result += f"Thumbnail URL: {source_thumbnail_url}\n"
    result += f"Duration: {source_duration}\n"
    result += f"Views: {source_view_count:,}\n"
    result += f"Days Online: {source_days_online}\n"
    result += f"Views Per Day: {source_views_per_day:,.1f}\n"
    result += f"Likes: {source_like_count:,}\n"
    result += f"Comments: {source_comment_count:,}\n"
    if source_subscriber_count > 0:
        result += f"Channel Subscribers: {source_subscriber_count:,}\n"
    result += f"Engagement Rate: {source_engagement_rate:.2f}%\n\n"
    
    # Comparison videos
    result += f"TOP {len(detailed_comparisons)} COMPARISON VIDEOS (by Views/Day):\n"
    
    for i, comp in enumerate(detailed_comparisons, 1):
        result += f"{i}. \"{comp['title']}\" by {comp['channel']}\n"
        result += f"   Category ID: {comp.get('category_id', 'Unknown')}\n"
        result += f"   Duration: {comp.get('duration', 'Unknown')}\n"
        result += f"   Definition: {comp.get('definition', 'Unknown')}\n"
        result += f"   Thumbnail URL: {comp['thumbnail_url']}\n"
        result += f"   Views: {comp['view_count']:,}\n"
        result += f"   Days Online: {comp.get('days_online', 0)}\n"
        result += f"   Views Per Day: {comp.get('views_per_day', 0):,.1f}\n"
        result += f"   Likes: {comp.get('like_count', 0):,}\n"
        result += f"   Comments: {comp.get('comment_count', 0):,}\n"
        result += f"   Engagement Rate: {comp['engagement_rate']:.2f}%\n"
        result += f"   Description: {comp.get('description', '')}\n"
        result += f"   Video URL: https://www.youtube.com/watch?v={comp['id']}\n\n"
    
    # Analysis and recommendations
    result += "THUMBNAIL ANALYSIS & RECOMMENDATIONS:\n"
    
    # Calculate time-normalized metrics for comparison
    avg_comp_views_per_day = sum(c.get("views_per_day", 0) for c in detailed_comparisons) / len(detailed_comparisons)
    avg_comp_engagement = sum(c["engagement_rate"] for c in detailed_comparisons) / len(detailed_comparisons)
    
    # Compare based on views per day (time-normalized metric)
    if source_views_per_day < avg_comp_views_per_day * 0.7:  # 30% below average
        result += "- Your thumbnail may be underperforming compared to similar videos.\n"
        result += f"  Your views/day: {source_views_per_day:.1f} vs. Average: {avg_comp_views_per_day:.1f}\n"
    elif source_views_per_day > avg_comp_views_per_day * 1.3:  # 30% above average
        result += "- Your thumbnail appears to be outperforming similar videos!\n"
        result += f"  Your views/day: {source_views_per_day:.1f} vs. Average: {avg_comp_views_per_day:.1f}\n"
    else:
        result += "- Your thumbnail performs similarly to others in this category.\n"
        result += f"  Your views/day: {source_views_per_day:.1f} vs. Average: {avg_comp_views_per_day:.1f}\n"
        
    # Also compare engagement rates as a secondary metric
    if source_engagement_rate < avg_comp_engagement * 0.7:  # 30% below average
        result += "- Your engagement rate is lower than similar videos.\n"
    elif source_engagement_rate > avg_comp_engagement * 1.3:  # 30% above average
        result += "- Your engagement rate is higher than similar videos.\n"
    
    # General recommendations based on industry best practices
    result += "- Suggested thumbnail improvements based on your comparisons:\n"
    result += "  * Use high contrast colors to stand out in search results\n"
    result += "  * Include clear, readable text (but not too much)\n"
    result += "  * Show emotional facial expressions if appropriate\n"
    result += "  * Ensure your thumbnail accurately represents your content\n"
    result += "  * Use the rule of thirds for balanced composition\n\n"
    
    result += "NOTE: For a complete analysis, visually compare your thumbnail with the\n"
    result += "comparison thumbnails by visiting the URLs provided. A/B testing different\n"
    result += "thumbnail styles is recommended for optimal results.\n"
    
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

@mcp.tool()
async def analyze_video_performance(video_id: str, time_period: int = 7, unit: str = "days") -> Dict[str, Any]:
    """Analyze performance metrics for a YouTube video over time.
    
    This function retrieves current metrics for a video and compares them with
    historical data to track growth and engagement trends.
    
    Args:
        video_id: The ID of the YouTube video to analyze
        time_period: Number of time units to analyze (default: 7)
        unit: Time unit for analysis - "days" or "hours" (default: "days")
    """
    # Validate input parameters
    if time_period <= 0:
        return {"error": "Time period must be a positive integer."}
        
    if unit not in ["days", "hours"]:
        return {"error": "Unit must be either 'days' or 'hours'."}
    
    # Get current video statistics
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": video_id
    }
    
    current_data = await make_youtube_request("videos", params)
    
    if "error" in current_data:
        return {"error": current_data["error"]}
    
    if "items" not in current_data or not current_data["items"]:
        return {"error": "Video not found or error fetching video information."}
    
    # Extract current metrics
    video = current_data["items"][0]
    snippet = video.get("snippet", {})
    statistics = video.get("statistics", {})
    
    title = snippet.get("title", "Unknown")
    channel = snippet.get("channelTitle", "Unknown")
    published_at = snippet.get("publishedAt", "Unknown")
    
    # Current metrics
    current_views = int(statistics.get("viewCount", 0))
    current_likes = int(statistics.get("likeCount", 0))
    current_comments = int(statistics.get("commentCount", 0))
    
    # Simulate historical data (in a real implementation, this would come from a database)
    # For demonstration purposes, we'll generate synthetic historical data
    # In a production environment, you would store and retrieve actual historical data
    
    import random
    from datetime import datetime, timedelta
    
    # Parse published date and ensure timezone consistency
    try:
        # Convert to timezone-naive datetime by stripping timezone info
        publish_date = datetime.fromisoformat(published_at.replace('Z', ''))
    except (ValueError, TypeError):
        publish_date = datetime.now() - timedelta(days=30)  # Fallback
    
    # Generate historical data points (simulated)
    historical_data = []
    today = datetime.now()  # This is timezone-naive
    
    # Determine how many data points we can generate based on video age
    if unit == "days":
        video_age_units = (today - publish_date).days
        time_unit_str = "days"
        format_str = "%Y-%m-%d"
    else:  # hours
        video_age_units = int((today - publish_date).total_seconds() / 3600)  # Convert to hours
        time_unit_str = "hours"
        format_str = "%Y-%m-%d %H:%M"
    
    data_points = min(time_period, video_age_units)
    
    if data_points <= 0:
        # Video is too new, just return current stats
        return {
            "result": f"Video '{title}' by {channel} is too new for historical analysis.\n\n"
                     f"Current Statistics:\n"
                     f"Views: {current_views:,}\n"
                     f"Likes: {current_likes:,}\n"
                     f"Comments: {current_comments:,}\n"
        }
    
    # Calculate approximate growth rates (for simulation)
    # In reality, these would come from stored historical data
    if unit == "days":
        unit_view_rate = current_views / max(video_age_units, 1)
        unit_like_rate = current_likes / max(video_age_units, 1)
        unit_comment_rate = current_comments / max(video_age_units, 1)
    else:  # hours
        # Hourly rates are typically lower than daily rates
        unit_view_rate = (current_views / max(video_age_units, 1)) * 0.8  # Adjust for hourly pattern
        unit_like_rate = (current_likes / max(video_age_units, 1)) * 0.8
        unit_comment_rate = (current_comments / max(video_age_units, 1)) * 0.8
    
    # Generate simulated historical data points with some randomness
    for i in range(data_points):
        units_ago = data_points - i
        
        if unit == "days":
            date = today - timedelta(days=units_ago)
        else:  # hours
            date = today - timedelta(hours=units_ago)
        
        # Add some randomness to make the data more realistic
        # Hourly data typically has more variance than daily data
        if unit == "days":
            randomness = lambda: random.uniform(0.85, 1.15)
        else:  # hours
            randomness = lambda: random.uniform(0.75, 1.25)  # More variance for hourly data
        
        # Calculate estimated metrics for this date
        est_views = int(max(0, current_views - (unit_view_rate * units_ago * randomness())))
        est_likes = int(max(0, current_likes - (unit_like_rate * units_ago * randomness())))
        est_comments = int(max(0, current_comments - (unit_comment_rate * units_ago * randomness())))
        
        historical_data.append({
            "date": date.strftime(format_str),
            "views": est_views,
            "likes": est_likes,
            "comments": est_comments
        })
    
    # Add current data point
    historical_data.append({
        "date": today.strftime(format_str),
        "views": current_views,
        "likes": current_likes,
        "comments": current_comments
    })
    
    # Calculate growth metrics
    first_data = historical_data[0]
    last_data = historical_data[-1]
    
    view_growth = last_data["views"] - first_data["views"]
    like_growth = last_data["likes"] - first_data["likes"]
    comment_growth = last_data["comments"] - first_data["comments"]
    
    view_growth_percent = (view_growth / max(first_data["views"], 1)) * 100
    like_growth_percent = (like_growth / max(first_data["likes"], 1)) * 100
    comment_growth_percent = (comment_growth / max(first_data["comments"], 1)) * 100
    
    # Calculate engagement rate (likes + comments per view)
    engagement_rate = ((current_likes + current_comments) / max(current_views, 1)) * 100
    
    # Format the results
    result = f"Performance Analysis for '{title}' by {channel}\n\n"
    
    # Current statistics
    result += "Current Statistics:\n"
    result += f"Views: {current_views:,}\n"
    result += f"Likes: {current_likes:,}\n"
    result += f"Comments: {current_comments:,}\n"
    result += f"Engagement Rate: {engagement_rate:.2f}%\n\n"
    
    # Growth over time period
    result += f"Growth over the past {data_points} {time_unit_str}:\n"
    result += f"Views: +{view_growth:,} ({view_growth_percent:.2f}%)\n"
    result += f"Likes: +{like_growth:,} ({like_growth_percent:.2f}%)\n"
    result += f"Comments: +{comment_growth:,} ({comment_growth_percent:.2f}%)\n\n"
    
    # Breakdown by time unit
    result += f"{time_unit_str.capitalize()} Breakdown:\n"
    for data in historical_data:
        result += f"{data['date']}: {data['views']:,} views, {data['likes']:,} likes, {data['comments']:,} comments\n"
    
    # Note about simulated data
    result += "\nNote: Historical data is simulated for demonstration purposes. In a production environment, actual historical data would be used."
    
    return {"result": result}

@mcp.tool()
async def create_live_broadcast(title: str, description: str, scheduled_start_time: str, privacy_status: str = "private", enable_dvr: bool = True, enable_auto_start: bool = True, enable_auto_stop: bool = True) -> Dict[str, Any]:
    """Create and schedule a YouTube live broadcast.
    
    This function creates a new live broadcast (livestream) on YouTube, making it easy to schedule
    upcoming streams programmatically. It handles both the broadcast and stream components required
    for a complete live streaming setup.
    
    Args:
        title: Title of the live broadcast (required)
        description: Description of the live broadcast (required)
        scheduled_start_time: ISO 8601 timestamp (YYYY-MM-DDThh:mm:ss.sssZ) for the scheduled start (required)
        privacy_status: Privacy status of the broadcast - 'private', 'public', or 'unlisted' (default: 'private')
        enable_dvr: Whether viewers can rewind the stream (default: True)
        enable_auto_start: Whether the broadcast should automatically start when streaming begins (default: True)
        enable_auto_stop: Whether the broadcast should automatically end when streaming stops (default: True)
    """
    # Validate input parameters
    if not title or not description or not scheduled_start_time:
        return {"error": "Title, description, and scheduled_start_time are required."}
    
    if privacy_status not in ["private", "public", "unlisted"]:
        return {"error": "Privacy status must be 'private', 'public', or 'unlisted'."}
    
    # Validate the timestamp format
    try:
        from datetime import datetime
        # Strip Z and add timezone information if needed
        if scheduled_start_time.endswith('Z'):
            scheduled_start_time = scheduled_start_time[:-1] + "+00:00"
        # Attempt to parse the time
        datetime.fromisoformat(scheduled_start_time)
    except ValueError:
        return {"error": "Invalid scheduled_start_time format. Use ISO 8601 format (YYYY-MM-DDThh:mm:ss.sssZ)"}
    
    # Step 1: Create the live broadcast
    broadcast_params = {
        "part": "snippet,status,contentDetails",
        "key": get_api_key()
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
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
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
                "key": get_api_key()
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
                "key": get_api_key()
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
            stream_key = stream_result.get("cdn", {}).get("ingestionInfo", {}).get("streamName", "Unknown")
            ingestion_address = stream_result.get("cdn", {}).get("ingestionInfo", {}).get("ingestionAddress", "Unknown")
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

@mcp.tool()
async def get_captions(video_id: str, language_code: str = None, format_type: str = "text") -> Dict[str, Any]:
    """Get captions/subtitles for a YouTube video.
    
    This function retrieves caption tracks for a video and returns either the list of available
    captions or the content of a specific caption track. Caption content can be returned in
    different formats including plain text, SRT, or WEBVTT.
    
    Args:
        video_id: The ID of the YouTube video
        language_code: ISO 639-1 language code (e.g., 'en', 'es', 'fr') for the desired caption track.
                      If None, returns a list of all available caption tracks.
        format_type: Format to return captions in - 'text' (plain text), 'srt' (SubRip), or 'vtt' (WebVTT)
                    Only used when a specific language_code is provided.
    """
    # First, get the list of caption tracks for the video
    params = {
        "part": "snippet",
        "videoId": video_id
    }
    
    data = await make_youtube_request("captions", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "No captions found for this video."}
    
    # If no language specified, return the list of available caption tracks
    if language_code is None:
        tracks = []
        for item in data["items"]:
            track_id = item.get("id", "Unknown")
            snippet = item.get("snippet", {})
            language = snippet.get("language", "Unknown")
            name = snippet.get("name", "")
            track_type = snippet.get("trackType", "Unknown")
            is_auto = track_type == "ASR"  # ASR means auto-generated by YouTube
            
            track_info = f"{language} ({name})" if name else language
            track_info += " (auto-generated)" if is_auto else ""
            
            tracks.append(f"{track_info} - ID: {track_id}")
        
        return {"result": f"Available caption tracks for video {video_id}:\n" + "\n".join(tracks)}
    
    # Find the requested caption track by language code
    caption_id = None
    for item in data["items"]:
        snippet = item.get("snippet", {})
        if snippet.get("language", "") == language_code:
            caption_id = item.get("id")
            break
    
    if not caption_id:
        return {"error": f"No caption track found for language '{language_code}'"}
    
    # Get the caption content
    # Note: The YouTube API doesn't directly support getting the caption content in the v3 API,
    # so we need to construct a different URL for fetching the actual caption data
    format_param = "fmt="
    if format_type.lower() == "srt":
        format_param += "srt"
    elif format_type.lower() == "vtt":
        format_param += "vtt"
    else:  # Default to plain text
        format_param += "text"
    
    # Construct the caption download URL
    # This requires a different authorization mechanism and endpoint
    api_key = get_api_key()
    caption_url = f"https://www.googleapis.com/youtube/v3/captions/{caption_id}?{format_param}&key={api_key}"
    
    # For captions, we need OAuth token which should be set in environment variables
    oauth_token = os.getenv("YOUTUBE_OAUTH_TOKEN")
    if not oauth_token:
        return {"error": "OAuth token required to access caption content. Set YOUTUBE_OAUTH_TOKEN environment variable."}
    
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Authorization": f"Bearer {oauth_token}"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(caption_url, headers=headers, timeout=30.0)
            response.raise_for_status()
            
            # Process caption content based on format requested
            caption_content = response.text
            
            # For plain text format, clean it up for better readability
            if format_type.lower() == "text":
                # Simple processing to make plain text more readable
                lines = caption_content.split("\n")
                processed_lines = []
                
                for line in lines:
                    # Remove timestamps and other formatting if present
                    if line.strip() and not line.strip()[0].isdigit() and "-->" not in line:
                        processed_lines.append(line)
                
                caption_content = "\n".join(processed_lines)
            
            # Format the result
            result = f"Captions for video {video_id} in {language_code}:\n\n"
            result += caption_content
            
            return {"result": result}
            
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
            # If we get a 403, it likely means we don't have rights to access this caption
            if e.response.status_code == 403:
                error_message = "Access denied. You may not have permission to access this caption track."
            return {"error": error_message}
            
        except Exception as e:
            return {"error": f"Error retrieving caption content: {str(e)}"}

@mcp.tool()
async def get_active_live_chat_id(video_id: str) -> Dict[str, Any]:
    """Get the active live chat ID for a YouTube livestream.
    
    This utility function retrieves the live chat ID for a currently active livestream,
    which is required for both retrieving and sending chat messages.
    
    Args:
        video_id: The ID of the YouTube livestream video
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
    streaming_details = video.get("liveStreamingDetails", {})
    live_chat_id = streaming_details.get("activeLiveChatId")
    
    if not live_chat_id:
        return {"error": "No active live chat found for this video. It may not be a livestream or the livestream may have ended."}
    
    return {
        "result": f"Active Live Chat ID: {live_chat_id}\n\nUse this ID with get_live_chat_messages or send_live_chat_message functions."
    }

@mcp.tool()
async def analyze_captions(video_id: str, language_code: str = "en", analysis_type: str = "keywords") -> Dict[str, Any]:
    """Analyze captions/subtitles for a YouTube video.
    
    This function retrieves a specific caption track for a video and performs various types of analysis
    on the content, such as extracting keywords, finding phrases, or generating a timeline breakdown.
    
    Args:
        video_id: The ID of the YouTube video
        language_code: ISO 639-1 language code (e.g., 'en', 'es', 'fr') for the desired caption track
        analysis_type: Type of analysis to perform - 'keywords', 'timeline', or 'phrases'
    """
    # First, use get_captions to retrieve the caption data
    # We'll use the SRT format for better timestamp processing
    params = {
        "part": "snippet",
        "videoId": video_id
    }
    
    data = await make_youtube_request("captions", params)
    
    if "error" in data:
        return {"error": data["error"]}
    
    if "items" not in data or not data["items"]:
        return {"error": "No captions found for this video."}
    
    # Find the requested caption track by language code
    caption_id = None
    for item in data["items"]:
        snippet = item.get("snippet", {})
        if snippet.get("language", "") == language_code:
            caption_id = item.get("id")
            break
    
    if not caption_id:
        return {"error": f"No caption track found for language '{language_code}'"}
    
    # Get the caption content in SRT format for better timestamp handling
    format_param = "fmt=srt"
    
    # Construct the caption download URL
    api_key = get_api_key()
    caption_url = f"https://www.googleapis.com/youtube/v3/captions/{caption_id}?{format_param}&key={api_key}"
    
    # For captions, we need OAuth token which should be set in environment variables
    oauth_token = os.getenv("YOUTUBE_OAUTH_TOKEN")
    if not oauth_token:
        return {"error": "OAuth token required to access caption content. Set YOUTUBE_OAUTH_TOKEN environment variable."}
    
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Authorization": f"Bearer {oauth_token}"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(caption_url, headers=headers, timeout=30.0)
            response.raise_for_status()
            
            # Parse SRT content
            srt_content = response.text
            caption_entries = parse_srt_captions(srt_content)
            
            if not caption_entries:
                return {"error": "Failed to parse caption content."}
            
            # Perform the requested analysis
            if analysis_type.lower() == "keywords":
                return analyze_caption_keywords(caption_entries, video_id, language_code)
            elif analysis_type.lower() == "timeline":
                return analyze_caption_timeline(caption_entries, video_id, language_code)
            elif analysis_type.lower() == "phrases":
                return analyze_caption_phrases(caption_entries, video_id, language_code)
            else:
                return {"error": f"Unknown analysis type: {analysis_type}. Use 'keywords', 'timeline', or 'phrases'."}
            
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
            if e.response.status_code == 403:
                error_message = "Access denied. You may not have permission to access this caption track."
            return {"error": error_message}
            
        except Exception as e:
            return {"error": f"Error analyzing caption content: {str(e)}"}


def parse_srt_captions(srt_content: str) -> List[Dict[str, Any]]:
    """Parse SRT format captions into structured data.
    
    Args:
        srt_content: String containing SRT format caption data
        
    Returns:
        List of caption entries with timing and text information
    """
    import re
    from datetime import datetime, timedelta
    
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


def analyze_caption_keywords(caption_entries: List[Dict[str, Any]], video_id: str, language_code: str) -> Dict[str, Any]:
    """Extract keywords from caption content.
    
    Args:
        caption_entries: List of parsed caption entries
        video_id: YouTube video ID
        language_code: Language code of the captions
        
    Returns:
        Dictionary with analysis results
    """
    import re
    from collections import Counter
    
    # Combine all caption text
    all_text = " ".join([entry["text"] for entry in caption_entries])
    
    # Clean the text
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', all_text)
    # Remove special characters and lowercase
    clean_text = re.sub(r'[^\w\s]', '', clean_text).lower()
    
    # Generate word frequency
    words = clean_text.split()
    
    # Remove common stop words (a basic set, could be expanded)
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been',
                 'have', 'has', 'had', 'do', 'does', 'did', 'to', 'from', 'in', 'out', 'on', 'off',
                 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
                 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most',
                 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
                 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now',
                 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your',
                 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her',
                 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs',
                 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those',
                 'am', 'um', 'uh', 'oh', 'like', 'yeah', 'gonna', 'go', 'get'}
    
    filtered_words = [word for word in words if word not in stop_words and len(word) > 1]
    word_freq = Counter(filtered_words)
    
    # Get top keywords
    top_keywords = word_freq.most_common(25)
    
    # Prepare result
    total_duration = caption_entries[-1]["end_seconds"]
    total_minutes = total_duration / 60
    total_word_count = len(words)
    
    result = f"Caption Analysis (Keywords) for video {video_id}:\n\n"
    result += f"Language: {language_code}\n"
    result += f"Duration: {int(total_minutes)} minutes {int(total_duration % 60)} seconds\n"
    result += f"Total Words: {total_word_count}\n"
    result += f"Words Per Minute: {int(total_word_count / total_minutes)}\n\n"
    
    result += "Top Keywords:\n"
    for i, (word, count) in enumerate(top_keywords, 1):
        result += f"{i}. {word}: {count} occurrences\n"
    
    return {"result": result}


def analyze_caption_timeline(caption_entries: List[Dict[str, Any]], video_id: str, language_code: str) -> Dict[str, Any]:
    """Generate a timeline breakdown of caption content.
    
    Args:
        caption_entries: List of parsed caption entries
        video_id: YouTube video ID
        language_code: Language code of the captions
        
    Returns:
        Dictionary with analysis results
    """
    # Divide the video into segments (e.g., 1-minute segments)
    segment_duration = 60  # 1 minute in seconds
    
    total_duration = caption_entries[-1]["end_seconds"]
    num_segments = int(total_duration / segment_duration) + 1
    
    segments = [[] for _ in range(num_segments)]
    
    # Distribute caption entries into segments
    for entry in caption_entries:
        segment_index = int(entry["start_seconds"] / segment_duration)
        if segment_index < len(segments):
            segments[segment_index].append(entry)
    
    # Generate a summary for each segment
    result = f"Caption Timeline for video {video_id}:\n\n"
    result += f"Language: {language_code}\n"
    result += f"Total Duration: {int(total_duration / 60)} minutes {int(total_duration % 60)} seconds\n\n"
    
    for i, segment in enumerate(segments):
        start_time = i * segment_duration
        end_time = min((i + 1) * segment_duration, total_duration)
        
        # Format timestamps as MM:SS
        start_formatted = f"{int(start_time / 60):02d}:{int(start_time % 60):02d}"
        end_formatted = f"{int(end_time / 60):02d}:{int(end_time % 60):02d}"
        
        if segment:  # Only include non-empty segments
            # Concatenate text from all entries in the segment
            segment_text = " ".join([entry["text"] for entry in segment])
            
            # Truncate if too long and add summary
            if len(segment_text) > 100:
                segment_text = segment_text[:97] + "..."
            
            result += f"{start_formatted} - {end_formatted}: {segment_text}\n\n"
    
    return {"result": result}


def analyze_caption_phrases(caption_entries: List[Dict[str, Any]], video_id: str, language_code: str) -> Dict[str, Any]:
    """Find common phrases and expressions in caption content.
    
    Args:
        caption_entries: List of parsed caption entries
        video_id: YouTube video ID
        language_code: Language code of the captions
        
    Returns:
        Dictionary with analysis results
    """
    import re
    from collections import Counter
    
    # Combine all caption text
    all_text = " ".join([entry["text"] for entry in caption_entries])
    
    # Clean the text
    clean_text = re.sub(r'<[^>]+>', '', all_text)  # Remove HTML tags
    
    # Extract n-grams (phrases of 2-4 words)
    def get_ngrams(text, n):
        words = re.findall(r'\b\w+\b', text.lower())
        ngrams = []
        
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i:i+n])
            ngrams.append(ngram)
            
        return ngrams
    
    # Get phrases of different lengths
    bigrams = get_ngrams(clean_text, 2)
    trigrams = get_ngrams(clean_text, 3)
    quadgrams = get_ngrams(clean_text, 4)
    
    # Count frequencies
    bigram_freq = Counter(bigrams)
    trigram_freq = Counter(trigrams)
    quadgram_freq = Counter(quadgrams)
    
    # Filter out common phrases that are likely not meaningful
    stop_bigrams = {'of the', 'in the', 'to the', 'on the', 'for the', 'with the', 'at the', 
                    'from the', 'by the', 'as the', 'is the', 'to be', 'in a', 'is a', 
                    'of a', 'it is', 'this is', 'that is', 'there is', 'i think', 'you know'}
    
    filtered_bigrams = {phrase: count for phrase, count in bigram_freq.items() 
                       if phrase not in stop_bigrams and count > 2}
    filtered_trigrams = {phrase: count for phrase, count in trigram_freq.items() if count > 2}
    filtered_quadgrams = {phrase: count for phrase, count in quadgram_freq.items() if count > 2}
    
    # Prepare result
    result = f"Caption Analysis (Phrases) for video {video_id}:\n\n"
    result += f"Language: {language_code}\n\n"
    
    # Add most common phrases
    result += "Frequent 2-Word Phrases:\n"
    for i, (phrase, count) in enumerate(sorted(filtered_bigrams.items(), key=lambda x: x[1], reverse=True)[:15], 1):
        result += f"{i}. \"{phrase}\" - {count} occurrences\n"
    
    result += "\nFrequent 3-Word Phrases:\n"
    for i, (phrase, count) in enumerate(sorted(filtered_trigrams.items(), key=lambda x: x[1], reverse=True)[:10], 1):
        result += f"{i}. \"{phrase}\" - {count} occurrences\n"
    
    result += "\nFrequent 4-Word Phrases:\n"
    for i, (phrase, count) in enumerate(sorted(filtered_quadgrams.items(), key=lambda x: x[1], reverse=True)[:5], 1):
        result += f"{i}. \"{phrase}\" - {count} occurrences\n"
    
    return {"result": result}

@mcp.tool()
async def get_live_chat_messages(live_chat_id: str, max_results: int = 20) -> Dict[str, Any]:
    """Get live chat messages from a YouTube livestream.
    
    This function retrieves messages from a live chat by its ID. The live chat ID can be obtained
    from the video details of a livestream using the get_video_details function.
    
    Args:
        live_chat_id: The ID of the live chat to retrieve messages from
        max_results: Maximum number of messages to return (default: 20, max: 200)
    """
    # Cap max_results to 200 (reasonable limit)
    if max_results > 200:
        max_results = 200
    
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
        snippet = item.get("snippet", {})
        author_details = item.get("authorDetails", {})
        
        # Get message content
        message_type = snippet.get("type", "Unknown")
        display_message = snippet.get("displayMessage", "[No message content]")
        published_at = snippet.get("publishedAt", "Unknown")
        
        # Get author information
        author_name = author_details.get("displayName", "Anonymous")
        author_channel_id = author_details.get("channelId", "Unknown")
        is_verified = author_details.get("isVerified", False)
        is_chat_owner = author_details.get("isChatOwner", False)
        is_chat_sponsor = author_details.get("isChatSponsor", False)
        is_chat_moderator = author_details.get("isChatModerator", False)
        
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

@mcp.tool()
async def send_live_chat_message(live_chat_id: str, message_text: str) -> Dict[str, Any]:
    """Send a message to a YouTube livestream chat.
    
    This function posts a message to a live chat by its ID. The sender must be authorized
    via OAuth and have permission to send messages in the specified chat.
    
    Args:
        live_chat_id: The ID of the live chat to send a message to
        message_text: The text content of the message to send
    """
    # Validate input parameters
    if not live_chat_id:
        return {"error": "Live chat ID is required."}
        
    if not message_text or len(message_text.strip()) == 0:
        return {"error": "Message text cannot be empty."}
    
    # Check for OAuth credentials
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    oauth_token = os.getenv("YOUTUBE_OAUTH_TOKEN")
    
    if not client_id or not client_secret or not oauth_token:
        return {"error": "OAuth credentials not available. Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, and YOUTUBE_OAUTH_TOKEN environment variables"}
    
    # Set up the API request
    params = {
        "part": "snippet",
        "key": get_api_key()
    }
    
    message_data = {
        "snippet": {
            "liveChatId": live_chat_id,
            "type": "textMessageEvent",
            "textMessageDetails": {
                "messageText": message_text
            }
        }
    }
    
    url = f"{YOUTUBE_API_BASE}/liveChat/messages"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth_token}"
    }
    
    # Make the API request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url, 
                headers=headers, 
                params=params, 
                json=message_data,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            # Check if the message was successfully posted
            if "id" in result:
                message_id = result["id"]
                snippet = result.get("snippet", {})
                author = snippet.get("authorDisplayName", "You")
                message = snippet.get("displayMessage", message_text)
                
                return {
                    "result": f"Message successfully sent to live chat!\n\nMessage ID: {message_id}\nAuthor: {author}\nContent: {message}"
                }
            else:
                return {"error": "Failed to send message. API did not return a message ID."}
                
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
            try:
                error_json = e.response.json()
                if "error" in error_json and "message" in error_json["error"]:
                    error_message = error_json["error"]["message"]
            except:
                pass
                
            return {"error": f"Failed to send message: {error_message}"}
            
        except Exception as e:
            return {"error": f"Unexpected error sending live chat message: {str(e)}"}

@mcp.tool()
async def get_audience_demographics(channel_id: str) -> Dict[str, Any]:
    """Get audience demographic information for a YouTube channel.
    
    This function retrieves demographic data about a channel's audience, including age groups,
    gender distribution, geographic location, and viewing device types. Requires OAuth.
    
    Args:
        channel_id: The ID of the YouTube channel to analyze
    """
    # Import the implementation from the audience_demographics module
    from audience_demographics import get_audience_demographics as get_demo_impl
    return await get_demo_impl(channel_id)

@mcp.tool()
async def get_channel_analytics(channel_id: str, metrics: List[str] = None, dimensions: List[str] = None, start_date: str = None, end_date: str = None, sort_by: str = None) -> Dict[str, Any]:
    """Get advanced analytics for a YouTube channel.
    
    This function retrieves YouTube Analytics data for a channel, providing creators
    with valuable insights about their channel performance over time. Requires OAuth.
    
    Args:
        channel_id: The ID of the YouTube channel to analyze
        metrics: List of metrics to retrieve (default: views, likes, subscribers)
        dimensions: List of dimensions to group by (default: day)
        start_date: Start date in ISO format YYYY-MM-DD (default: 30 days ago)
        end_date: End date in ISO format YYYY-MM-DD (default: today)
        sort_by: Metric to sort by (default: date ascending)
    """
    # Import required datetime libraries
    from datetime import datetime, timedelta
    
    # Validate and set up default parameters
    if metrics is None:
        metrics = ["views", "likes", "subscribersGained", "subscribersLost", "estimatedMinutesWatched", "averageViewDuration"]
    
    if dimensions is None:
        dimensions = ["day"]
    
    # Generate default dates if not provided (last 30 days)
    today = datetime.now().strftime("%Y-%m-%d")
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    if not start_date:
        start_date = thirty_days_ago
    
    if not end_date:
        end_date = today
    
    # Check for OAuth credentials
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    oauth_token = os.getenv("YOUTUBE_OAUTH_TOKEN")
    
    if not client_id or not client_secret or not oauth_token:
        return {"error": "OAuth credentials not available. Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, and YOUTUBE_OAUTH_TOKEN environment variables"}
    
    # Prepare headers with authorization
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Authorization": f"Bearer {oauth_token}"
    }
    
    # First, validate the channel ID and get channel info
    channel_params = {
        "part": "snippet,contentDetails",
        "id": channel_id,
        "key": get_api_key()
    }
    
    channel_data = await make_youtube_request("channels", channel_params)
    
    if "error" in channel_data:
        return {"error": channel_data["error"]}
    
    if "items" not in channel_data or not channel_data["items"]:
        return {"error": "Channel not found or error fetching channel information."}
    
    # Get content owner ID if available (for YouTube partner channels)
    content_owner_id = None
    try:
        content_owner_id = channel_data["items"][0].get("contentOwnerDetails", {}).get("contentOwner")
    except (KeyError, IndexError):
        pass
    
    # Construct the YouTube Analytics API request
    analytics_base_url = "https://youtubeanalytics.googleapis.com/v2/reports"
    
    # Prepare parameters
    analytics_params = {
        "ids": f"channel=={channel_id}",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": ",".join(metrics),
        "dimensions": ",".join(dimensions)
    }
    
    # Add sorting parameter if provided
    if sort_by:
        analytics_params["sort"] = sort_by
    
    # If content owner ID is available and we're authorized, we can use it
    if content_owner_id:
        analytics_params["ids"] = f"contentOwner=={content_owner_id}"
    
    # Make the API request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                analytics_base_url, 
                headers=headers, 
                params=analytics_params,
                timeout=30.0
            )
            response.raise_for_status()
            analytics_data = response.json()
            
            # Process the analytics data for better readability
            if "rows" not in analytics_data or not analytics_data["rows"]:
                return {"error": "No analytics data available for this channel or time period."}
            
            # Get column headers
            column_headers = [header.get("name") for header in analytics_data.get("columnHeaders", [])]
            
            # Format the results
            channel_title = channel_data["items"][0].get("snippet", {}).get("title", "Unknown Channel")
            
            result = f"Analytics for {channel_title} (ID: {channel_id})\n"
            result += f"Period: {start_date} to {end_date}\n\n"
            
            # Add totals if available
            if "rows" in analytics_data and analytics_data["rows"]:
                # If we have dimension=day, we need to calculate totals manually
                if "day" in dimensions:
                    totals = {metric: 0 for metric in metrics}
                    for row in analytics_data["rows"]:
                        for i, value in enumerate(row):
                            if i >= len(dimensions):  # Skip dimension columns
                                metric_name = column_headers[i]
                                if metric_name in totals:
                                    totals[metric_name] += value
                    
                    result += "Channel Totals:\n"
                    for metric, total in totals.items():
                        # Format numbers appropriately
                        if metric in ["views", "likes", "subscribersGained", "subscribersLost", "comments"]:
                            result += f"{metric}: {total:,}\n"
                        elif metric in ["estimatedMinutesWatched"]:
                            result += f"{metric}: {total:,} minutes ({total/60:,.1f} hours)\n"
                        elif metric in ["averageViewDuration"]:
                            result += f"{metric}: {total/len(analytics_data['rows']):,.1f} seconds\n"
                        else:
                            result += f"{metric}: {total}\n"
                else:
                    # For non-time-based dimensions, just display the rows directly
                    result += "Breakdown by {dimensions[0]}:\n"
            
            # Add daily/dimensional breakdown
            result += "\nDetailed Breakdown:\n"
            
            # Create a header row
            header_row = "\t".join(column_headers)
            result += f"{header_row}\n"
            result += "-" * len(header_row) + "\n"
            
            # Add data rows
            for row in analytics_data["rows"]:
                formatted_row = []
                for i, value in enumerate(row):
                    if i < len(dimensions) and dimensions[i] == "day":
                        # Format date nicely
                        formatted_row.append(value)  # Keep ISO format for dates
                    elif isinstance(value, (int, float)) and value > 1000:
                        # Format large numbers with commas
                        formatted_row.append(f"{value:,}")
                    else:
                        formatted_row.append(str(value))
                
                result += "\t".join(formatted_row) + "\n"
            
            # Add insights section to highlight key metrics
            result += "\nInsights:\n"
            
            # Calculate growth rates and trends
            if "day" in dimensions and len(analytics_data["rows"]) > 1:
                # Calculate day-over-day growth for key metrics
                try:
                    for metric_index, metric in enumerate(metrics):
                        dimension_offset = len(dimensions)
                        metric_index += dimension_offset
                        
                        if metric in ["views", "subscribersGained", "likes"]:
                            first_day = analytics_data["rows"][0][metric_index]
                            last_day = analytics_data["rows"][-1][metric_index]
                            total = sum(row[metric_index] for row in analytics_data["rows"])
                            
                            # Only calculate averages and growth if we have data
                            if total > 0:
                                daily_avg = total / len(analytics_data["rows"])
                                
                                if first_day > 0:
                                    growth_rate = ((last_day - first_day) / first_day) * 100
                                    trend = "increasing" if growth_rate > 5 else "decreasing" if growth_rate < -5 else "stable"
                                    
                                    result += f"- {metric.capitalize()}: Daily average of {daily_avg:,.1f}, trend is {trend} "  
                                    if growth_rate > 0:
                                        result += f"(+{growth_rate:,.1f}%)\n"
                                    else:
                                        result += f"({growth_rate:,.1f}%)\n"
                except Exception as e:
                    result += f"- Error calculating insights: {str(e)}\n"
            
            # Calculate engagement metrics if we have the data
            if "likes" in metrics and "views" in metrics:
                try:
                    likes_index = metrics.index("likes") + len(dimensions)
                    views_index = metrics.index("views") + len(dimensions)
                    
                    total_likes = sum(row[likes_index] for row in analytics_data["rows"])
                    total_views = sum(row[views_index] for row in analytics_data["rows"])
                    
                    if total_views > 0:
                        like_rate = (total_likes / total_views) * 100
                        result += f"- Like rate: {like_rate:.2f}% of viewers like your videos\n"
                except Exception:
                    pass
            
            # Calculate retention metrics if we have the data
            if "estimatedMinutesWatched" in metrics and "views" in metrics:
                try:
                    minutes_index = metrics.index("estimatedMinutesWatched") + len(dimensions)
                    views_index = metrics.index("views") + len(dimensions)
                    
                    total_minutes = sum(row[minutes_index] for row in analytics_data["rows"])
                    total_views = sum(row[views_index] for row in analytics_data["rows"])
                    
                    if total_views > 0:
                        avg_minutes_per_view = total_minutes / total_views
                        result += f"- Average watch time: {avg_minutes_per_view:.2f} minutes per view\n"
                except Exception:
                    pass
            
            # Calculate subscriber metrics if we have the data
            if "subscribersGained" in metrics and "subscribersLost" in metrics:
                try:
                    gained_index = metrics.index("subscribersGained") + len(dimensions)
                    lost_index = metrics.index("subscribersLost") + len(dimensions)
                    
                    total_gained = sum(row[gained_index] for row in analytics_data["rows"])
                    total_lost = sum(row[lost_index] for row in analytics_data["rows"])
                    net_change = total_gained - total_lost
                    
                    result += f"- Subscriber change: {net_change:+,} ({total_gained:,} gained, {total_lost:,} lost)\n"
                    
                    if total_gained > 0:
                        retention_rate = (1 - (total_lost / total_gained)) * 100
                        result += f"- Subscriber retention rate: {retention_rate:.1f}%\n"
                except Exception:
                    pass
            
            # Add a note about YouTube Analytics
            result += "\nNote: For more detailed analytics, visit YouTube Studio.\n"
            
            return {"result": result}
            
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
            try:
                error_json = e.response.json()
                if "error" in error_json and "message" in error_json["error"]:
                    error_message = error_json["error"]["message"]
            except:
                pass
                
            return {"error": f"Failed to retrieve analytics: {error_message}"}
            
        except Exception as e:
            return {"error": f"Unexpected error retrieving analytics: {str(e)}"}

@mcp.tool()
async def upload_video(file_path: str, title: str, description: str, privacy_status: str = "private", tags: List[str] = None, 
                    category_id: str = "22", notify_subscribers: bool = True, language: str = "en", 
                    location_latitude: float = None, location_longitude: float = None, 
                    made_for_kids: bool = False) -> Dict[str, Any]:
    """Upload a video to YouTube with complete metadata.
    
    This function uploads a video file to YouTube and sets all available metadata, providing
    a comprehensive solution for programmatic video uploads.
    
    Args:
        file_path: Local path to the video file
        title: Title of the video (required)
        description: Description of the video (required)
        privacy_status: Privacy status - 'private', 'public', or 'unlisted' (default: 'private')
        tags: List of tags/keywords for the video (default: None)
        category_id: YouTube category ID (default: '22' for People & Blogs)
                    Common categories: '1'=Film, '2'=Autos, '10'=Music, '15'=Pets, '17'=Sports, '20'=Gaming, '22'=People, '23'=Comedy, '24'=Entertainment, '25'=News, '26'=How-to, '27'=Education, '28'=Science
        notify_subscribers: Whether to notify subscribers about this upload (default: True)
        language: ISO 639-1 language code (default: 'en')
        location_latitude: Latitude for video geo-tagging (default: None)
        location_longitude: Longitude for video geo-tagging (default: None)
        made_for_kids: Whether this content is made for children (default: False)
    """
    # Validate input parameters
    if not file_path or not title or not description:
        return {"error": "File path, title, and description are required."}
    
    if privacy_status not in ["private", "public", "unlisted"]:
        return {"error": "Privacy status must be 'private', 'public', or 'unlisted'."}
    
    # Check if file exists
    import os
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    
    # Get file size and verify it's not too large (YouTube limits apply)
    file_size = os.path.getsize(file_path)
    max_file_size = 128 * 1024 * 1024 * 1024  # 128GB is YouTube's max for verified accounts
    if file_size > max_file_size:
        return {"error": f"File is too large. YouTube's maximum is 128GB, file is {file_size / (1024*1024*1024):.2f}GB"}
    
    # Determine MIME type based on file extension
    import mimetypes
    file_ext = os.path.splitext(file_path)[1].lower()
    mime_type = mimetypes.types_map.get(file_ext, "video/mp4")
    
    # Validate MIME type is acceptable for YouTube
    acceptable_mime_types = ["video/mp4", "video/x-m4v", "video/quicktime", "video/mpeg", "video/webm", "video/x-flv", "video/3gpp"]
    if mime_type not in acceptable_mime_types:
        return {"error": f"File type {mime_type} is not supported by YouTube. Supported types: {', '.join(acceptable_mime_types)}"}
    
    try:
        # Import libraries needed for the upload
        import httplib2
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from oauth2client.client import OAuth2WebServerFlow
        import apiclient.discovery
    except ImportError:
        return {"error": "Required Python libraries not installed. Please install: 'google-api-python-client', 'oauth2client', 'httplib2'"}
    
    # Check for API key and OAuth credentials
    api_key = get_api_key()
    if not api_key:
        return {"error": "YouTube API key not available"}
        
    # Get OAuth credentials
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    oauth_token = os.getenv("YOUTUBE_OAUTH_TOKEN")
    
    if not client_id or not client_secret or not oauth_token:
        return {"error": "OAuth credentials not available. Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, and YOUTUBE_OAUTH_TOKEN environment variables"}
    
    # Initialize the API client
    try:
        credentials = OAuth2WebServerFlow(client_id=client_id, client_secret=client_secret, 
                                         token_uri="https://oauth2.googleapis.com/token",
                                         access_token=oauth_token)
        
        http = credentials.authorize(httplib2.Http())
        youtube = build('youtube', 'v3', http=http)
    except Exception as e:
        return {"error": f"Error initializing YouTube API client: {str(e)}"}
    
    # Set up the metadata for the video
    video_metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags if tags else [],
            "categoryId": category_id,
            "defaultLanguage": language,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": made_for_kids,
            "publishAt": None,  # Immediate upload
            "embeddable": True,
            "publicStatsViewable": True
        },
        "notifySubscribers": notify_subscribers
    }
    
    # Add location if provided
    if location_latitude is not None and location_longitude is not None:
        video_metadata["snippet"]["recordingDetails"] = {
            "location": {
                "latitude": location_latitude,
                "longitude": location_longitude
            }
        }
    
    # Set up the media file
    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True, chunksize=1024*1024)
    
    # Create the request
    insert_request = youtube.videos().insert(
        part="snippet,status",
        body=video_metadata,
        media_body=media
    )
    
    # Execute the chunked upload
    video_id = None
    response = None
    
    print(f"Starting upload of {file_path} ({file_size / (1024*1024):.2f} MB)", file=sys.stderr)
    
    try:
        status, response = insert_request.next_chunk()
        while status is not None:
            # Calculate upload progress
            if status.total_size > 0:
                progress = int(status.resumable_progress * 100 / status.total_size)
                print(f"Upload progress: {progress}%", file=sys.stderr)
            status, response = insert_request.next_chunk()
            
        if response is not None:
            if 'id' in response:
                video_id = response['id']
                print(f"Video upload complete! Video ID: {video_id}", file=sys.stderr)
            else:
                return {"error": "Video upload failed. No video ID in the response."}
        else:
            return {"error": "Video upload failed. Empty response from API."}
            
    except Exception as e:
        return {"error": f"Error during video upload: {str(e)}"}
    
    # Return success response with video details
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    edit_url = f"https://studio.youtube.com/video/{video_id}/edit"
    
    result = f"""Successfully uploaded video to YouTube!

Video Details:
Title: {title}
Privacy Status: {privacy_status}
Video ID: {video_id}

Links:
Video URL: {video_url}
Edit in YouTube Studio: {edit_url}

Important Notes:
- YouTube may still be processing your video in different resolutions
- Thumbnail generation and indexing might take some time
- If set to 'public', the video is already visible to everyone
"""
    
    return {"result": result}
