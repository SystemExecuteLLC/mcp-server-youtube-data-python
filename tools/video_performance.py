"""
Tool for analyzing performance metrics of a YouTube video over time.
"""

from typing import Any, Dict, List
import random
from datetime import datetime, timedelta
from api_client import make_youtube_request
from utils import safe_get, format_number

async def analyze_video_performance(video_id: str, time_period: int = 7, unit: str = "days") -> Dict[str, Any]:
    """Analyze performance metrics for a YouTube video over time.
    
    This function retrieves current metrics for a video and compares them with
    historical data to track growth and engagement trends.
    
    Args:
        video_id: The ID of the YouTube video to analyze
        time_period: Number of time units to analyze (default: 7)
        unit: Time unit for analysis - "days" or "hours" (default: "days")
        
    Returns:
        Dict containing performance analysis or error
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
    snippet = safe_get(video, "snippet", default={})
    statistics = safe_get(video, "statistics", default={})
    
    title = safe_get(snippet, "title", default="Unknown")
    channel = safe_get(snippet, "channelTitle", default="Unknown")
    published_at = safe_get(snippet, "publishedAt", default="Unknown")
    
    # Current metrics
    current_views = int(safe_get(statistics, "viewCount", default=0))
    current_likes = int(safe_get(statistics, "likeCount", default=0))
    current_comments = int(safe_get(statistics, "commentCount", default=0))
    
    # Simulate historical data (in a real implementation, this would come from a database)
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
            "result": (
                f"Video '{title}' by {channel} is too new for historical analysis.\n\n"
                f"Current Statistics:\n"
                f"Views: {format_number(current_views)}\n"
                f"Likes: {format_number(current_likes)}\n"
                f"Comments: {format_number(current_comments)}\n"
            )
        }
    
    # Calculate approximate growth rates (for simulation)
    if unit == "days":
        unit_view_rate = current_views / max(video_age_units, 1)
        unit_like_rate = current_likes / max(video_age_units, 1)
        unit_comment_rate = current_comments / max(video_age_units, 1)
    else:  # hours
        # Hourly rates are typically lower than daily rates
        unit_view_rate = (current_views / max(video_age_units, 1)) * 0.8  # Adjust for hourly pattern
        unit_like_rate = (current_likes / max(video_age_units, 1)) * 0.8
        unit_comment_rate = (current_comments / max(video_age_units, 1)) * 0.8
    
    # Generate simulated historical data points with randomness
    for i in range(data_points):
        units_ago = data_points - i
        
        if unit == "days":
            date = today - timedelta(days=units_ago)
        else:  # hours
            date = today - timedelta(hours=units_ago)
        
        # Add randomness to make the data more realistic
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
    result += f"Views: {format_number(current_views)}\n"
    result += f"Likes: {format_number(current_likes)}\n"
    result += f"Comments: {format_number(current_comments)}\n"
    result += f"Engagement Rate: {engagement_rate:.2f}%\n\n"
    
    # Growth over time period
    result += f"Growth over the past {data_points} {time_unit_str}:\n"
    result += f"Views: +{format_number(view_growth)} ({view_growth_percent:.2f}%)\n"
    result += f"Likes: +{format_number(like_growth)} ({like_growth_percent:.2f}%)\n"
    result += f"Comments: +{format_number(comment_growth)} ({comment_growth_percent:.2f}%)\n\n"
    
    # Breakdown by time unit
    result += f"{time_unit_str.capitalize()} Breakdown:\n"
    for data in historical_data:
        result += (
            f"{data['date']}: {format_number(data['views'])} views, "
            f"{format_number(data['likes'])} likes, "
            f"{format_number(data['comments'])} comments\n"
        )
    
    # Note about simulated data
    result += (
        "\nNote: Historical data is simulated for demonstration purposes. "
        "In a production environment, actual historical data would be used."
    )
    
    return {"result": result}
