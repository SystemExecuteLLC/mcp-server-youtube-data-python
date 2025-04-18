# YouTube Metrics Collector

This document outlines the implementation plan for a data collection system to track YouTube video performance metrics over time. The system will enhance the `analyze_video_performance` function by replacing simulated historical data with actual collected metrics.

## Background

The YouTube Data API v3 provides current metrics (views, likes, comments) at the time of request but does not offer historical data points. To analyze performance over time, we need to build a system that:

1. Regularly polls the YouTube API for metrics on tracked videos
2. Stores these metrics with timestamps in a database
3. Provides an interface to query and analyze the collected data

## Implementation Options

### Basic Implementation (1-2 days)

A simple implementation that provides core functionality with minimal development effort.

#### Database Schema

Using SQLite for simplicity:

```sql
-- Videos being tracked
CREATE TABLE videos (
    video_id TEXT PRIMARY KEY,
    title TEXT,
    channel_id TEXT,
    channel_title TEXT,
    published_at TIMESTAMP,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Metrics snapshots
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    views INTEGER,
    likes INTEGER,
    comments INTEGER,
    FOREIGN KEY (video_id) REFERENCES videos(video_id)
);

-- Create index for efficient querying
CREATE INDEX idx_metrics_video_time ON metrics(video_id, timestamp);
```

#### Data Collection Service

A simple Python script that runs on a schedule:

```python
# metrics_collector.py
import sqlite3
import asyncio
import schedule
import time
import sys
from datetime import datetime

# Import the YouTube API functions
sys.path.append('/path/to/mcp-server-youtube-data-python')
from youtube_api import make_youtube_request

# Database setup
DB_PATH = 'youtube_metrics.db'

def init_db():
    """Initialize the database if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create videos table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        video_id TEXT PRIMARY KEY,
        title TEXT,
        channel_id TEXT,
        channel_title TEXT,
        published_at TIMESTAMP,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create metrics table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        views INTEGER,
        likes INTEGER,
        comments INTEGER,
        FOREIGN KEY (video_id) REFERENCES videos(video_id)
    )
    ''')
    
    # Create index
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_metrics_video_time ON metrics(video_id, timestamp)
    ''')
    
    conn.commit()
    conn.close()

async def collect_metrics():
    """Collect metrics for all tracked videos."""
    print(f"Starting metrics collection at {datetime.now()}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all tracked videos
    cursor.execute("SELECT video_id FROM videos")
    videos = cursor.fetchall()
    
    for video in videos:
        video_id = video[0]
        try:
            # Get current metrics from YouTube API
            params = {
                "part": "snippet,statistics",
                "id": video_id
            }
            
            data = await make_youtube_request("videos", params)
            
            if "error" in data:
                print(f"Error fetching data for video {video_id}: {data['error']}")
                continue
                
            if "items" not in data or not data["items"]:
                print(f"No data found for video {video_id}")
                continue
                
            # Extract metrics
            video_data = data["items"][0]
            statistics = video_data.get("statistics", {})
            
            views = int(statistics.get("viewCount", 0))
            likes = int(statistics.get("likeCount", 0))
            comments = int(statistics.get("commentCount", 0))
            
            # Store in database
            cursor.execute(
                "INSERT INTO metrics (video_id, timestamp, views, likes, comments) VALUES (?, ?, ?, ?, ?)",
                (video_id, datetime.now(), views, likes, comments)
            )
            
            print(f"Collected metrics for video {video_id}: {views} views, {likes} likes, {comments} comments")
            
        except Exception as e:
            print(f"Error processing video {video_id}: {str(e)}")
    
    conn.commit()
    conn.close()
    print(f"Completed metrics collection at {datetime.now()}")

async def register_video(video_id):
    """Register a new video for tracking."""
    try:
        # Get video details from YouTube API
        params = {
            "part": "snippet",
            "id": video_id
        }
        
        data = await make_youtube_request("videos", params)
        
        if "error" in data:
            return {"error": data["error"]}
            
        if "items" not in data or not data["items"]:
            return {"error": "Video not found"}
            
        # Extract video details
        video_data = data["items"][0]
        snippet = video_data.get("snippet", {})
        
        title = snippet.get("title", "Unknown")
        channel_id = snippet.get("channelId", "Unknown")
        channel_title = snippet.get("channelTitle", "Unknown")
        published_at = snippet.get("publishedAt", datetime.now().isoformat())
        
        # Store in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR REPLACE INTO videos (video_id, title, channel_id, channel_title, published_at) VALUES (?, ?, ?, ?, ?)",
            (video_id, title, channel_id, channel_title, published_at)
        )
        
        conn.commit()
        conn.close()
        
        # Collect initial metrics
        await collect_metrics()
        
        return {"result": f"Video '{title}' registered for tracking"}
        
    except Exception as e:
        return {"error": f"Error registering video: {str(e)}"}

def run_scheduler():
    """Run the scheduler to collect metrics at regular intervals."""
    init_db()
    
    # Schedule collection every hour
    schedule.every(1).hour.do(lambda: asyncio.run(collect_metrics()))
    
    print("Metrics collector started. Press Ctrl+C to exit.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("Metrics collector stopped.")

if __name__ == "__main__":
    run_scheduler()
```

#### Integration with MCP Server

Modify the `analyze_video_performance` function to use the collected data:

```python
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
    
    # Connect to the metrics database
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        DB_PATH = 'youtube_metrics.db'
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if video is being tracked
        cursor.execute("SELECT title, channel_title FROM videos WHERE video_id = ?", (video_id,))
        video_info = cursor.fetchone()
        
        if not video_info:
            # Video not tracked, fall back to current data only
            params = {
                "part": "snippet,statistics",
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
            
            # Register video for future tracking
            cursor.execute(
                "INSERT INTO videos (video_id, title, channel_id, channel_title, published_at) VALUES (?, ?, ?, ?, ?)",
                (video_id, title, snippet.get("channelId", "Unknown"), channel, snippet.get("publishedAt", datetime.now().isoformat()))
            )
            
            # Store current metrics
            cursor.execute(
                "INSERT INTO metrics (video_id, timestamp, views, likes, comments) VALUES (?, ?, ?, ?, ?)",
                (
                    video_id, 
                    datetime.now(), 
                    int(statistics.get("viewCount", 0)),
                    int(statistics.get("likeCount", 0)),
                    int(statistics.get("commentCount", 0))
                )
            )
            
            conn.commit()
            
            return {
                "result": f"Video '{title}' by {channel} has been registered for tracking.\n\n"
                         f"Current Statistics:\n"
                         f"Views: {statistics.get('viewCount', 0):,}\n"
                         f"Likes: {statistics.get('likeCount', 0):,}\n"
                         f"Comments: {statistics.get('commentCount', 0):,}\n\n"
                         f"No historical data is available yet. Check back later for performance analysis."
            }
        
        # Video is being tracked, get historical data
        title, channel = video_info
        
        # Calculate time range
        end_time = datetime.now()
        if unit == "days":
            start_time = end_time - timedelta(days=time_period)
        else:  # hours
            start_time = end_time - timedelta(hours=time_period)
            
        # Query for metrics in the time range
        cursor.execute(
            "SELECT timestamp, views, likes, comments FROM metrics WHERE video_id = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp",
            (video_id, start_time, end_time)
        )
        
        metrics_data = cursor.fetchall()
        
        if not metrics_data:
            return {"error": f"No metrics data available for video '{title}' in the specified time range."}
            
        # Process the data
        historical_data = []
        for timestamp_str, views, likes, comments in metrics_data:
            try:
                # Parse timestamp
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = timestamp_str
                    
                historical_data.append({
                    "date": timestamp.strftime("%Y-%m-%d %H:%M" if unit == "hours" else "%Y-%m-%d"),
                    "views": views,
                    "likes": likes,
                    "comments": comments
                })
            except Exception as e:
                print(f"Error parsing timestamp {timestamp_str}: {str(e)}")
                
        # Get the first and last data points
        first_data = historical_data[0] if historical_data else None
        last_data = historical_data[-1] if historical_data else None
        
        if not first_data or not last_data:
            return {"error": "Error processing metrics data."}
            
        # Calculate growth metrics
        view_growth = last_data["views"] - first_data["views"]
        like_growth = last_data["likes"] - first_data["likes"]
        comment_growth = last_data["comments"] - first_data["comments"]
        
        view_growth_percent = (view_growth / max(first_data["views"], 1)) * 100
        like_growth_percent = (like_growth / max(first_data["likes"], 1)) * 100
        comment_growth_percent = (comment_growth / max(first_data["comments"], 1)) * 100
        
        # Calculate engagement rate
        engagement_rate = ((last_data["likes"] + last_data["comments"]) / max(last_data["views"], 1)) * 100
        
        # Format the results
        time_unit_str = "hours" if unit == "hours" else "days"
        result = f"Performance Analysis for '{title}' by {channel}\n\n"
        
        # Current statistics
        result += "Current Statistics:\n"
        result += f"Views: {last_data['views']:,}\n"
        result += f"Likes: {last_data['likes']:,}\n"
        result += f"Comments: {last_data['comments']:,}\n"
        result += f"Engagement Rate: {engagement_rate:.2f}%\n\n"
        
        # Growth over time period
        result += f"Growth over the past {time_period} {time_unit_str}:\n"
        result += f"Views: +{view_growth:,} ({view_growth_percent:.2f}%)\n"
        result += f"Likes: +{like_growth:,} ({like_growth_percent:.2f}%)\n"
        result += f"Comments: +{comment_growth:,} ({comment_growth_percent:.2f}%)\n\n"
        
        # Data points breakdown
        result += f"{time_unit_str.capitalize()} Breakdown:\n"
        for data in historical_data:
            result += f"{data['date']}: {data['views']:,} views, {data['likes']:,} likes, {data['comments']:,} comments\n"
        
        return {"result": result}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Error analyzing video performance: {str(e)}"}
```

#### Add Registration Tool

Add a new tool to register videos for tracking:

```python
@mcp.tool()
async def register_video_for_tracking(video_id: str) -> Dict[str, Any]:
    """Register a YouTube video for performance tracking.
    
    This function adds a video to the tracking database so that metrics
    will be collected regularly for future analysis.
    
    Args:
        video_id: The ID of the YouTube video to track
    """
    try:
        import sqlite3
        from datetime import datetime
        
        # Get video details from YouTube API
        params = {
            "part": "snippet",
            "id": video_id
        }
        
        data = await make_youtube_request("videos", params)
        
        if "error" in data:
            return {"error": data["error"]}
            
        if "items" not in data or not data["items"]:
            return {"error": "Video not found or error fetching video information."}
            
        # Extract video details
        video_data = data["items"][0]
        snippet = video_data.get("snippet", {})
        
        title = snippet.get("title", "Unknown")
        channel_id = snippet.get("channelId", "Unknown")
        channel_title = snippet.get("channelTitle", "Unknown")
        published_at = snippet.get("publishedAt", datetime.now().isoformat())
        
        # Store in database
        DB_PATH = 'youtube_metrics.db'
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            channel_id TEXT,
            channel_title TEXT,
            published_at TIMESTAMP,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            views INTEGER,
            likes INTEGER,
            comments INTEGER,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
        ''')
        
        # Register the video
        cursor.execute(
            "INSERT OR REPLACE INTO videos (video_id, title, channel_id, channel_title, published_at) VALUES (?, ?, ?, ?, ?)",
            (video_id, title, channel_id, channel_title, published_at)
        )
        
        # Get initial metrics
        params = {
            "part": "statistics",
            "id": video_id
        }
        
        stats_data = await make_youtube_request("videos", params)
        
        if "items" in stats_data and stats_data["items"]:
            statistics = stats_data["items"][0].get("statistics", {})
            
            # Store initial metrics
            cursor.execute(
                "INSERT INTO metrics (video_id, timestamp, views, likes, comments) VALUES (?, ?, ?, ?, ?)",
                (
                    video_id, 
                    datetime.now(), 
                    int(statistics.get("viewCount", 0)),
                    int(statistics.get("likeCount", 0)),
                    int(statistics.get("commentCount", 0))
                )
            )
        
        conn.commit()
        conn.close()
        
        return {"result": f"Video '{title}' by {channel_title} has been registered for tracking."}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Error registering video: {str(e)}"}
```

### Robust Implementation (1-2 weeks)

For a production-grade system, we would expand on the basic implementation with these enhancements:

#### Advanced Database

Use a time-series database like TimescaleDB (PostgreSQL extension) for efficient storage and querying of time-based metrics:

```sql
-- Create extension (if using PostgreSQL)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Videos being tracked
CREATE TABLE videos (
    video_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    channel_title TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'active',
    metadata JSONB
);

-- Metrics snapshots
CREATE TABLE metrics (
    time TIMESTAMPTZ NOT NULL,
    video_id TEXT NOT NULL,
    views BIGINT,
    likes BIGINT,
    comments BIGINT,
    shares BIGINT,
    favorites BIGINT,
    estimated_revenue NUMERIC(10,2),
    watch_time_minutes BIGINT,
    average_view_duration NUMERIC(10,2),
    FOREIGN KEY (video_id) REFERENCES videos(video_id)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('metrics', 'time');

-- Create indexes
CREATE INDEX idx_videos_channel ON videos(channel_id);
CREATE INDEX idx_metrics_video_id ON metrics(video_id);
```

#### Reliable Collection Service

Implement a robust collection service using Celery for distributed task processing:

```python
# tasks.py
from celery import Celery
from celery.schedules import crontab
import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import Json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("metrics_collector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("metrics_collector")

# Import the YouTube API functions
sys.path.append('/path/to/mcp-server-youtube-data-python')
from youtube_api import make_youtube_request

# Configure Celery
app = Celery('youtube_metrics')
app.conf.update(
    broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'collect-hourly-metrics': {
            'task': 'tasks.collect_all_metrics',
            'schedule': crontab(minute=0),  # Run at the top of every hour
        },
        'check-video-status': {
            'task': 'tasks.check_video_status',
            'schedule': crontab(hour=0, minute=0),  # Run daily at midnight
        },
    }
)

# Database connection
def get_db_connection():
    """Get a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        database=os.environ.get('DB_NAME', 'youtube_metrics'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'postgres')
    )

@app.task
def collect_all_metrics():
    """Collect metrics for all tracked videos."""
    logger.info("Starting metrics collection")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all active tracked videos
        cursor.execute("SELECT video_id FROM videos WHERE status = 'active'")
        videos = cursor.fetchall()
        
        for video in videos:
            video_id = video[0]
            # Schedule individual collection tasks
            collect_video_metrics.delay(video_id)
        
        cursor.close()
        conn.close()
        
        logger.info(f"Scheduled metrics collection for {len(videos)} videos")
        return f"Scheduled metrics collection for {len(videos)} videos"
    
    except Exception as e:
        logger.error(f"Error scheduling metrics collection: {str(e)}")
        return f"Error: {str(e)}"

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_video_metrics(self, video_id):
    """Collect metrics for a specific video with retries."""
    logger.info(f"Collecting metrics for video {video_id}")
    
    try:
        # Run the async function to get metrics
        loop = asyncio.get_event_loop()
        data = loop.run_until_complete(_get_video_metrics(video_id))
        
        if "error" in data:
            logger.error(f"API error for video {video_id}: {data['error']}")
            raise Exception(data["error"])
        
        # Store metrics in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO metrics (time, video_id, views, likes, comments, shares, favorites)
            VALUES (NOW(), %s, %s, %s, %s, %s, %s)
            """,
            (
                video_id,
                data["views"],
                data["likes"],
                data["comments"],
                data.get("shares", 0),
                data.get("favorites", 0)
            )
        )
        
        # Update last_updated timestamp
        cursor.execute(
            "UPDATE videos SET last_updated = NOW() WHERE video_id = %s",
            (video_id,)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully collected metrics for video {video_id}")
        return f"Successfully collected metrics for video {video_id}"
        
    except Exception as e:
        logger.error(f"Error collecting metrics for video {video_id}: {str(e)}")
        # Retry with exponential backoff
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for video {video_id}")
            return f"Failed after multiple attempts: {str(e)}"

async def _get_video_metrics(video_id):
    """Get current metrics from YouTube API."""
    params = {
        "part": "statistics",
        "id": video_id
    }
    
    data = await make_youtube_request("videos", params)
    
    if "error" in data:
        return {"error": data["error"]}
        
    if "items" not in data or not data["items"]:
        return {"error": "Video not found"}
        
    statistics = data["items"][0].get("statistics", {})
    
    return {
        "views": int(statistics.get("viewCount", 0)),
        "likes": int(statistics.get("likeCount", 0)),
        "comments": int(statistics.get("commentCount", 0)),
        "favorites": int(statistics.get("favoriteCount", 0))
    }

@app.task
def check_video_status():
    """Check if tracked videos still exist and update their status."""
    logger.info("Checking video status")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all active tracked videos
        cursor.execute("SELECT video_id FROM videos WHERE status = 'active'")
        videos = cursor.fetchall()
        
        for video in videos:
            video_id = video[0]
            # Schedule individual status check tasks
            check_single_video_status.delay(video_id)
        
        cursor.close()
        conn.close()
        
        logger.info(f"Scheduled status checks for {len(videos)} videos")
        return f"Scheduled status checks for {len(videos)} videos"
    
    except Exception as e:
        logger.error(f"Error scheduling video status checks: {str(e)}")
        return f"Error: {str(e)}"

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def check_single_video_status(self, video_id):
    """Check if a specific video still exists."""
    logger.info(f"Checking status for video {video_id}")
    
    try:
        # Run the async function to check video
        loop = asyncio.get_event_loop()
        data = loop.run_until_complete(_check_video_exists(video_id))
        
        # Update video status in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if "error" in data:
            # Video might be deleted or private
            cursor.execute(
                "UPDATE videos SET status = 'unavailable', metadata = %s WHERE video_id = %s",
                (Json({"error": data["error"], "checked_at": datetime.now().isoformat()}), video_id)
            )
            logger.warning(f"Video {video_id} marked as unavailable: {data['error']}")
        else:
            # Video exists, update metadata
            cursor.execute(
                "UPDATE videos SET status = 'active', metadata = %s WHERE video_id = %s",
                (Json({"checked_at": datetime.now().isoformat()}), video_id)
            )
            logger.info(f"Video {video_id} confirmed active")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return f"Status check completed for video {video_id}"
        
    except Exception as e:
        logger.error(f"Error checking status for video {video_id}: {str(e)}")
        # Retry with exponential backoff
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for video {video_id}")
            return f"Failed after multiple attempts: {str(e)}"

async def _check_video_exists(video_id):
    """Check if a video still exists on YouTube."""
    params = {
        "part": "id",
        "id": video_id
    }
    
    data = await make_youtube_request("videos", params)
    
    if "error" in data:
        return {"error": data["error"]}
        
    if "items" not in data or not data["items"]:
        return {"error": "Video not found or no longer available"}
        
    return {"status": "active"}

@app.task
def register_new_video(video_id):
    """Register a new video for tracking."""
    logger.info(f"Registering new video {video_id}")
    
    try:
        # Run the async function to get video details
        loop = asyncio.get_event_loop()
        data = loop.run_until_complete(_get_video_details(video_id))
        
        if "error" in data:
            logger.error(f"Error getting details for video {video_id}: {data['error']}")
            return {"error": data["error"]}
        
        # Store video in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO videos (video_id, title, channel_id, channel_title, published_at, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
            ON CONFLICT (video_id) 
            DO UPDATE SET 
                title = EXCLUDED.title,
                channel_id = EXCLUDED.channel_id,
                channel_title = EXCLUDED.channel_title,
                published_at = EXCLUDED.published_at,
                status = 'active',
                last_updated = NOW()
            """,
            (
                video_id,
                data["title"],
                data["channel_id"],
                data["channel_title"],
                data["published_at"]
            )
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Collect initial metrics
        collect_video_metrics.delay(video_id)
        
        logger.info(f"Successfully registered video {video_id}")
        return {"result": f"Video '{data['title']}' registered for tracking"}
        
    except Exception as e:
        logger.error(f"Error registering video {video_id}: {str(e)}")
        return {"error": f"Error registering video: {str(e)}"}

async def _get_video_details(video_id):
    """Get video details from YouTube API."""
    params = {
        "part": "snippet",
        "id": video_id
    }
    
    data = await make_youtube_request("videos", params)
    
    if
