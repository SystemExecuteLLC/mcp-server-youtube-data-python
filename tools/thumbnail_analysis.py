"""
Tool for analyzing YouTube video thumbnail effectiveness.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from api_client import make_youtube_request
from utils import safe_get, format_number

async def analyze_thumbnail_effectiveness(
    video_id: str, 
    num_comparisons: int = 5, 
    category_id: str = None
) -> Dict[str, Any]:
    """Analyze thumbnail effectiveness for a YouTube video by comparing with similar high-performing videos.
    
    This function compares a video's thumbnail against thumbnails from similar successful videos,
    providing insights that can help creators optimize their thumbnails for better click-through rates.
    
    Args:
        video_id: The ID of the YouTube video to analyze
        num_comparisons: Number of similar videos to compare (default: 5, max: 10)
        category_id: Optional category ID to filter comparison videos (default: None, uses the video's category)
    
    Returns:
        Dict containing thumbnail analysis or error
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
    snippet = safe_get(source_video, "snippet", default={})
    statistics = safe_get(source_video, "statistics", default={})
    content_details = safe_get(source_video, "contentDetails", default={})
    
    source_title = safe_get(snippet, "title", default="Unknown")
    source_description = safe_get(snippet, "description", default="")
    source_channel_id = safe_get(snippet, "channelId", default="")
    source_channel_title = safe_get(snippet, "channelTitle", default="Unknown")
    source_tags = safe_get(snippet, "tags", default=[])
    source_view_count = int(safe_get(statistics, "viewCount", default=0))
    source_like_count = int(safe_get(statistics, "likeCount", default=0))
    source_comment_count = int(safe_get(statistics, "commentCount", default=0))
    source_duration = safe_get(content_details, "duration", default="Unknown")
    
    # Get or use provided category ID
    if category_id is None:
        category_id = safe_get(snippet, "categoryId", default="")
    
    # Extract thumbnail URLs
    source_thumbnails = safe_get(snippet, "thumbnails", default={})
    source_thumbnail_url = (
        safe_get(source_thumbnails, "maxres", "url") or
        safe_get(source_thumbnails, "high", "url") or
        safe_get(source_thumbnails, "default", "url", default="None")
    )
    
    # Step 2: Get channel details for engagement context
    channel_params = {
        "part": "statistics",
        "id": source_channel_id
    }
    
    channel_data = await make_youtube_request("channels", channel_params)
    
    source_subscriber_count = 0
    if "items" in channel_data and channel_data["items"]:
        channel = channel_data["items"][0]
        source_subscriber_count = int(safe_get(channel, "statistics", "subscriberCount", default=0))
    
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
    # Simple keyword extraction by removing common words
    stop_words = {
        'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
        'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'to', 'from', 'by', 'for', 'with', 'about', 'against', 'between',
        'into', 'during', 'before', 'after', 'above', 'below', 'at', 'in',
        'on', 'of', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
        'she', 'it', 'we', 'they', 'how', 'what', 'why', 'when', 'where'
    }
    
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
        video_id_from_search = safe_get(item, "id", "videoId", default="")
        channel_id_from_search = safe_get(item, "snippet", "channelId", default="")
        
        if video_id_from_search != video_id and channel_id_from_search != source_channel_id:
            comparison_videos.append(item)
            
            if len(comparison_videos) >= num_comparisons:
                break
    
    if not comparison_videos:
        return {"error": "Could not find suitable comparison videos."}
    
    # Get detailed information for comparison videos
    comparison_video_ids = [
        safe_get(v, "id", "videoId", default="") for v in comparison_videos
    ]
    
    # Get details for comparison videos
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
        comp_snippet = safe_get(item, "snippet", default={})
        comp_statistics = safe_get(item, "statistics", default={})
        comp_content_details = safe_get(item, "contentDetails", default={})
        
        # Get thumbnail URLs
        comp_thumbnails = safe_get(comp_snippet, "thumbnails", default={})
        comp_thumbnail_url = (
            safe_get(comp_thumbnails, "maxres", "url") or
            safe_get(comp_thumbnails, "high", "url") or
            safe_get(comp_thumbnails, "default", "url", default="None")
        )
        
        # Get publish date for time-based metrics
        published_at = safe_get(comp_snippet, "publishedAt", default="")
        
        # Get other detailed info
        video_duration = safe_get(comp_content_details, "duration", default="Unknown")
        video_definition = safe_get(comp_content_details, "definition", default="Unknown").upper()
        comment_count = int(safe_get(comp_statistics, "commentCount", default=0))
        description = safe_get(comp_snippet, "description", default="")
        if len(description) > 100:
            description = description[:100] + "..."
        
        # Extract category name if available
        category_id = safe_get(comp_snippet, "categoryId", default="")
        
        # Video details
        comparison = {
            "id": safe_get(item, "id", default=""),
            "title": safe_get(comp_snippet, "title", default="Unknown"),
            "channel": safe_get(comp_snippet, "channelTitle", default="Unknown"),
            "thumbnail_url": comp_thumbnail_url,
            "published_at": published_at,
            "duration": video_duration,
            "definition": video_definition,
            "description": description,
            "category_id": category_id,
            "view_count": int(safe_get(comp_statistics, "viewCount", default=0)),
            "like_count": int(safe_get(comp_statistics, "likeCount", default=0)),
            "comment_count": comment_count
        }
        
        # Calculate engagement rate
        if comparison["view_count"] > 0:
            comparison["engagement_rate"] = (comparison["like_count"] / comparison["view_count"]) * 100
        else:
            comparison["engagement_rate"] = 0
            
        # Calculate time-based metrics
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
    
    # Format the analysis results
    result = f"Thumbnail Effectiveness Analysis for '{source_title}' by {source_channel_title}\n\n"
    
    # Add time-based metrics for source video
    current_time = datetime.now(timezone.utc)
    
    source_published_at = safe_get(snippet, "publishedAt", default="")
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
    result += f"Views: {format_number(source_view_count)}\n"
    result += f"Days Online: {source_days_online}\n"
    result += f"Views Per Day: {source_views_per_day:,.1f}\n"
    result += f"Likes: {format_number(source_like_count)}\n"
    result += f"Comments: {format_number(source_comment_count)}\n"
    if source_subscriber_count > 0:
        result += f"Channel Subscribers: {format_number(source_subscriber_count)}\n"
    result += f"Engagement Rate: {source_engagement_rate:.2f}%\n\n"
    
    # Comparison videos
    result += f"TOP {len(detailed_comparisons)} COMPARISON VIDEOS (by Views/Day):\n"
    
    for i, comp in enumerate(detailed_comparisons, 1):
        result += f"{i}. \"{comp['title']}\" by {comp['channel']}\n"
        result += f"   Category ID: {comp.get('category_id', 'Unknown')}\n"
        result += f"   Duration: {comp.get('duration', 'Unknown')}\n"
        result += f"   Definition: {comp.get('definition', 'Unknown')}\n"
        result += f"   Thumbnail URL: {comp['thumbnail_url']}\n"
        result += f"   Views: {format_number(comp['view_count'])}\n"
        result += f"   Days Online: {comp.get('days_online', 0)}\n"
        result += f"   Views Per Day: {comp.get('views_per_day', 0):,.1f}\n"
        result += f"   Likes: {format_number(comp.get('like_count', 0))}\n"
        result += f"   Comments: {format_number(comp.get('comment_count', 0))}\n"
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
