## Continuation of Robust Implementation

This file continues from where `youtube_metrics_collector.md` was truncated.

### Completing the Celery Tasks Implementation

```python
async def _get_video_details(video_id):
    """Get video details from YouTube API."""
    params = {
        "part": "snippet",
        "id": video_id
    }
    
    data = await make_youtube_request("videos", params)
    
    if "error" in data:
        return {"error": data["error"]}
        
    if "items" not in data or not data["items"]:
        return {"error": "Video not found"}
        
    video_data = data["items"][0]
    snippet = video_data.get("snippet", {})
    
    return {
        "title": snippet.get("title", "Unknown"),
        "channel_id": snippet.get("channelId", "Unknown"),
        "channel_title": snippet.get("channelTitle", "Unknown"),
        "published_at": snippet.get("publishedAt", datetime.now().isoformat())
    }
```

### Admin Interface

For a complete solution, we would also implement an admin interface to manage the tracking system:

#### Web Dashboard (Flask/FastAPI)

```python
# app.py
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import os
import asyncio
from tasks import register_new_video, collect_video_metrics

app = FastAPI(title="YouTube Metrics Tracker")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    """Get database connection."""
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        database=os.environ.get('DB_NAME', 'youtube_metrics'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'postgres')
    )
    conn.cursor_factory = psycopg2.extras.DictCursor
    try:
        yield conn
    finally:
        conn.close()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: psycopg2.extensions.connection = Depends(get_db)):
    """Main dashboard page."""
    cursor = db.cursor()
    
    # Get summary statistics
    cursor.execute("SELECT COUNT(*) FROM videos WHERE status = 'active'")
    active_videos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM metrics WHERE time > NOW() - INTERVAL '24 hours'")
    metrics_last_24h = cursor.fetchone()[0]
    
    # Get recent videos
    cursor.execute(
        """
        SELECT video_id, title, channel_title, added_at, last_updated
        FROM videos
        WHERE status = 'active'
        ORDER BY added_at DESC
        LIMIT 10
        """
    )
    recent_videos = cursor.fetchall()
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_videos": active_videos,
            "metrics_last_24h": metrics_last_24h,
            "recent_videos": recent_videos
        }
    )

@app.get("/videos")
async def list_videos(
    db: psycopg2.extensions.connection = Depends(get_db),
    status: Optional[str] = Query("active", description="Filter by status (active, unavailable, all)"),
    channel_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """List tracked videos with filtering."""
    cursor = db.cursor()
    
    query = "SELECT video_id, title, channel_id, channel_title, published_at, added_at, last_updated, status FROM videos"
    params = []
    
    # Apply filters
    conditions = []
    if status != "all":
        conditions.append("status = %s")
        params.append(status)
    
    if channel_id:
        conditions.append("channel_id = %s")
        params.append(channel_id)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY added_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    videos = cursor.fetchall()
    
    # Get total count for pagination
    count_query = "SELECT COUNT(*) FROM videos"
    if conditions:
        count_query += " WHERE " + " AND ".join(conditions)
    
    cursor.execute(count_query, params[:-2] if params else [])
    total = cursor.fetchone()[0]
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "videos": [dict(video) for video in videos]
    }

@app.post("/videos/{video_id}/register")
async def register_video(video_id: str):
    """Register a new video for tracking."""
    task = register_new_video.delay(video_id)
    return {"task_id": task.id, "message": "Video registration started"}

@app.get("/videos/{video_id}/metrics")
async def get_video_metrics(
    video_id: str,
    db: psycopg2.extensions.connection = Depends(get_db),
    days: int = Query(7, ge=1, le=365),
    interval: str = Query("day", description="Aggregation interval (hour, day, week, month)")
):
    """Get metrics for a specific video."""
    cursor = db.cursor()
    
    # Check if video exists
    cursor.execute("SELECT title, channel_title FROM videos WHERE video_id = %s", (video_id,))
    video = cursor.fetchone()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Get time-series data with appropriate aggregation
    if interval == "hour":
        time_trunc = "hour"
    elif interval == "day":
        time_trunc = "day"
    elif interval == "week":
        time_trunc = "week"
    elif interval == "month":
        time_trunc = "month"
    else:
        raise HTTPException(status_code=400, detail="Invalid interval")
    
    cursor.execute(
        f"""
        SELECT 
            time_bucket('{interval}', time) AS period,
            MAX(views) AS views,
            MAX(likes) AS likes,
            MAX(comments) AS comments
        FROM metrics
        WHERE video_id = %s AND time > NOW() - INTERVAL '{days} days'
        GROUP BY period
        ORDER BY period
        """,
        (video_id,)
    )
    
    metrics = cursor.fetchall()
    
    # Calculate growth rates
    if len(metrics) >= 2:
        first = metrics[0]
        last = metrics[-1]
        
        view_growth = last["views"] - first["views"]
        view_growth_pct = (view_growth / first["views"] * 100) if first["views"] > 0 else 0
        
        like_growth = last["likes"] - first["likes"]
        like_growth_pct = (like_growth / first["likes"] * 100) if first["likes"] > 0 else 0
        
        comment_growth = last["comments"] - first["comments"]
        comment_growth_pct = (comment_growth / first["comments"] * 100) if first["comments"] > 0 else 0
        
        growth = {
            "views": {
                "absolute": view_growth,
                "percent": view_growth_pct
            },
            "likes": {
                "absolute": like_growth,
                "percent": like_growth_pct
            },
            "comments": {
                "absolute": comment_growth,
                "percent": comment_growth_pct
            }
        }
    else:
        growth = None
    
    return {
        "video": dict(video),
        "metrics": [dict(m) for m in metrics],
        "growth": growth,
        "period": {
            "days": days,
            "interval": interval
        }
    }

@app.post("/videos/{video_id}/collect")
async def trigger_metrics_collection(video_id: str):
    """Manually trigger metrics collection for a video."""
    task = collect_video_metrics.delay(video_id)
    return {"task_id": task.id, "message": "Metrics collection started"}

@app.delete("/videos/{video_id}")
async def delete_video(
    video_id: str,
    db: psycopg2.extensions.connection = Depends(get_db),
    delete_metrics: bool = Query(False, description="Whether to delete associated metrics")
):
    """Remove a video from tracking."""
    cursor = db.cursor()
    
    # Check if video exists
    cursor.execute("SELECT title FROM videos WHERE video_id = %s", (video_id,))
    video = cursor.fetchone()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if delete_metrics:
        cursor.execute("DELETE FROM metrics WHERE video_id = %s", (video_id,))
    
    cursor.execute("DELETE FROM videos WHERE video_id = %s", (video_id,))
    db.commit()
    
    return {"message": f"Video '{video['title']}' removed from tracking"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Deployment Considerations

For a production deployment, consider the following:

1. **Docker Containerization**:
   - Create separate containers for:
     - Web API/Admin interface
     - Celery workers
     - Celery beat scheduler
     - PostgreSQL/TimescaleDB
     - Redis (for Celery broker)

2. **Environment Configuration**:
   - Use environment variables for all configuration
   - Store sensitive information (API keys, database credentials) in a secure vault

3. **Monitoring and Alerting**:
   - Set up Prometheus/Grafana for metrics monitoring
   - Configure alerts for:
     - Failed collection tasks
     - API quota usage approaching limits
     - Database storage issues

4. **Scaling Considerations**:
   - Horizontal scaling of Celery workers for handling more videos
   - Database partitioning for large metric collections
   - Implement rate limiting to respect YouTube API quotas

5. **Backup Strategy**:
   - Regular database backups
   - Point-in-time recovery capability

## Integration with MCP Server

To fully integrate this system with the existing MCP server, we would:

1. Add the modified `analyze_video_performance` function to `youtube_api.py`
2. Add the new `register_video_for_tracking` function to `youtube_api.py`
3. Set up the data collection service as a separate process
4. Configure the database connection details

The MCP server would then be able to provide detailed historical analysis while the collection service runs independently to gather metrics over time.

## Conclusion

This implementation plan provides both a simple starting point (1-2 days of work) and a path to a robust, production-ready system (1-2 weeks). The basic implementation can be quickly deployed to start collecting data, while the more advanced features can be added incrementally as needed.

By collecting actual historical data rather than simulating it, the `analyze_video_performance` function will provide much more accurate and valuable insights into video performance trends, including the ability to analyze hourly performance for newly published videos.
