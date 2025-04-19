# YouTube Data API MCP Server

## LLM links for building this:
https://chatgpt.com/c/6801d2b2-7a84-8007-94e1-1139c132a160


This project provides an MCP (Managed Cloud Project) server for accessing the YouTube Data API v3. The server exposes YouTube functionality through a standardized MCP interface.

## Getting the discovery JSON:
curl https://www.googleapis.com/discovery/v1/apis/youtube/v3/rest \ -o youtube-v3-discovery.json


## pip installation while using uv (note single ticks for certain packages):
uv pip install 'mcp[cli]'  
uv pip install python-dotenv

## Debugging:
mcp dev youtube_api.py 

## Setup - Note TBC - use pipx, seems to play nicely with uv
source .venv/bin/activate ## activates the environment that is stored in the local .venv folder

uv pip install -r requirements.txt
uv run python youtube_api.py

### Prerequisites

- Python 3.9+
- A Google Cloud project with the YouTube Data API v3 enabled
- A YouTube API key
- (For creator analytics): OAuth 2.0 credentials

## Gap analysis of implementation vs discovery file
uv python gap_analysis.py

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/mcp-server-youtube-data-python.git
   cd mcp-server-youtube-data-python
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set your YouTube API key as an environment variable:
   ```bash
   export YOUTUBE_API_KEY="your-api-key-here"
   ```

   For Windows Command Prompt:
   ```cmd
   set YOUTUBE_API_KEY=your-api-key-here
   ```

   For Windows PowerShell:
   ```powershell
   $env:YOUTUBE_API_KEY="your-api-key-here"
   ```

4. For creator analytics features, set OAuth credentials:
   ```bash
   export YOUTUBE_CLIENT_ID="your-client-id"
   export YOUTUBE_CLIENT_SECRET="your-client-secret"
   export YOUTUBE_OAUTH_TOKEN="your-oauth-token"
   ```

## Running the Server

Start the MCP server:

```bash
python youtube_api.py
```

## Available Tools

### Basic Channel and Video Tools

### `get_channel_info`

Gets information about a YouTube channel.

Parameters:
- `channel_id`: The ID of the YouTube channel

Example:
```
get_channel_info(channel_id="UCXuqSBlHAE6Xw-yeJA0Tunw")
```

### `search_videos`

Searches for YouTube videos based on a query.

Parameters:
- `query`: Search query string
- `max_results`: Maximum number of results to return (default: 10, max: 50)

Example:
```
search_videos(query="machine learning tutorial", max_results=5)
```

### `get_video_details`

Gets detailed information about a YouTube video.

Parameters:
- `video_id`: The ID of the YouTube video

Example:
```
get_video_details(video_id="dQw4w9WgXcQ")
```

### `list_channel_videos`

Lists videos from a specific YouTube channel.

Parameters:
- `channel_id`: The ID of the YouTube channel
- `max_results`: Maximum number of results to return (default: 10, max: 50)

Example:
```
list_channel_videos(channel_id="UCXuqSBlHAE6Xw-yeJA0Tunw", max_results=5)
```

### `get_playlist_details`

Gets details about a YouTube playlist and its videos.

Parameters:
- `playlist_id`: The ID of the YouTube playlist
- `max_results`: Maximum number of videos to return (default: 10, max: 50)

Example:
```
get_playlist_details(playlist_id="PL59LTecnGM1NRUyune3SxzZlYpZezK-oQ")
```

### `get_video_comments`

Gets comments for a YouTube video.

Parameters:
- `video_id`: The ID of the YouTube video
- `max_results`: Maximum number of comments to return (default: 10, max: 100)

Example:
```
get_video_comments(video_id="dQw4w9WgXcQ", max_results=20)
```

### `search_by_topic`

Searches for YouTube videos related to a specific Freebase topic.

Parameters:
- `topic_id`: The Freebase topic ID
- `max_results`: Maximum number of results to return (default: 10, max: 50)

Example:
```
search_by_topic(topic_id="/m/0d6lp", max_results=5)
```

### Creator Analytics Tools (Requires OAuth)

### `get_channel_analytics`

Gets advanced performance analytics for a YouTube channel.

Parameters:
- `channel_id`: The ID of the YouTube channel to analyze
- `metrics`: List of metrics to retrieve (default: views, likes, subscribers)
- `dimensions`: List of dimensions to group by (default: day)
- `start_date`: Start date in ISO format YYYY-MM-DD (default: 30 days ago)
- `end_date`: End date in ISO format YYYY-MM-DD (default: today)
- `sort_by`: Metric to sort by (default: date ascending)

Example:
```
get_channel_analytics(channel_id="your-channel-id", metrics=["views", "subscribersGained"], start_date="2023-01-01")
```

### `get_audience_demographics`

Gets detailed audience demographics for a YouTube channel.

Parameters:
- `channel_id`: The ID of the YouTube channel to analyze

Example:
```
get_audience_demographics(channel_id="your-channel-id")
```

### `analyze_video_performance`

Analyzes performance metrics for a specific video over time.

Parameters:
- `video_id`: The ID of the YouTube video to analyze
- `time_period`: Number of time units to analyze (default: 7)
- `unit`: Time unit for analysis - "days" or "hours" (default: "days")

Example:
```
analyze_video_performance(video_id="your-video-id", time_period=14)
```

### `get_channel_subscriptions`

Gets a list of channels that the specified channel is subscribed to.
Note: This requires OAuth authorization and only works with the authenticated user's channel.

Parameters:
- `channel_id`: The ID of the YouTube channel (must be authorized user's channel)
- `max_results`: Maximum number of results to return (default: 10, max: 50)

Example:
```
get_channel_subscriptions(channel_id="your-authorized-channel-id")
```

### Livestream and Video Management Tools (Requires OAuth)

### `create_live_broadcast`

Creates and schedules a YouTube live broadcast.

Parameters:
- `title`: Title of the live broadcast
- `description`: Description of the live broadcast
- `scheduled_start_time`: ISO 8601 timestamp for the scheduled start
- `privacy_status`: Privacy status - 'private', 'public', or 'unlisted' (default: 'private')
- `enable_dvr`: Whether viewers can rewind the stream (default: True)
- `enable_auto_start`: Whether the broadcast should automatically start (default: True)
- `enable_auto_stop`: Whether the broadcast should automatically end (default: True)

Example:
```
create_live_broadcast(title="My Live Stream", description="A test live stream", scheduled_start_time="2023-12-31T18:00:00Z")
```

### `get_active_live_chat_id`

Gets the active live chat ID for a YouTube livestream.

Parameters:
- `video_id`: The ID of the YouTube livestream video

Example:
```
get_active_live_chat_id(video_id="your-livestream-id")
```

### `get_live_chat_messages`

Gets live chat messages from a YouTube livestream.

Parameters:
- `live_chat_id`: The ID of the live chat to retrieve messages from
- `max_results`: Maximum number of messages to return (default: 20, max: 200)

Example:
```
get_live_chat_messages(live_chat_id="your-live-chat-id", max_results=50)
```

### `send_live_chat_message`

Sends a message to a YouTube livestream chat.

Parameters:
- `live_chat_id`: The ID of the live chat to send a message to
- `message_text`: The text content of the message to send

Example:
```
send_live_chat_message(live_chat_id="your-live-chat-id", message_text="Hello from the API!")
```

### `upload_video`

Uploads a video to YouTube with complete metadata.

Parameters:
- `file_path`: Local path to the video file
- `title`: Title of the video
- `description`: Description of the video
- `privacy_status`: Privacy status - 'private', 'public', or 'unlisted' (default: 'private')
- `tags`: List of tags/keywords for the video (default: None)
- `category_id`: YouTube category ID (default: '22' for People & Blogs)
- `notify_subscribers`: Whether to notify subscribers (default: True)
- `language`: ISO 639-1 language code (default: 'en')
- `location_latitude`: Latitude for video geo-tagging (default: None)
- `location_longitude`: Longitude for video geo-tagging (default: None)
- `made_for_kids`: Whether this content is made for children (default: False)

Example:
```
upload_video(file_path="/path/to/video.mp4", title="My Video", description="A test video upload")
```

### Caption and Transcript Tools (Requires OAuth)

### `get_captions`

Gets captions/subtitles for a YouTube video.

Parameters:
- `video_id`: The ID of the YouTube video
- `language_code`: ISO 639-1 language code (e.g., 'en', 'es', 'fr') (default: None returns list of available captions)
- `format_type`: Format to return captions in - 'text', 'srt', or 'vtt' (default: 'text')

Example:
```
get_captions(video_id="your-video-id", language_code="en")
```

### `analyze_captions`

Analyzes captions/subtitles for a YouTube video.

Parameters:
- `video_id`: The ID of the YouTube video
- `language_code`: ISO 639-1 language code (default: "en")
- `analysis_type`: Type of analysis - 'keywords', 'timeline', or 'phrases' (default: 'keywords')

Example:
```
analyze_captions(video_id="your-video-id", analysis_type="phrases")
```

## Available Resources

### `youtube://status`

Checks if the YouTube API is configured correctly.

### `youtube://trending`

Gets the current trending videos on YouTube.

### `youtube://categories`

Gets a list of YouTube video categories.

### `youtube://recommendations/{video_id}`

Gets YouTube video recommendations based on a video ID or trending videos.

Parameters:
- `video_id`: Optional ID of a video to get recommendations for

## Extending the Server

This server can be extended with additional tools and resources by following the MCP server pattern. To add new functionality:

1. Add a new tool or resource method in `youtube_api.py`
2. Use the `@mcp.tool()` or `@mcp.resource()` decorators
3. Restart the server to apply changes

## Troubleshooting

- If you receive authentication errors, make sure your API key is set correctly
- For OAuth-required functions, ensure your OAuth credentials are valid and have the necessary scopes
- Check the server logs for detailed error information
- Ensure your API key has the necessary permissions for the YouTube Data API v3

## License

N/A (Private)
