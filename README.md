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

## Running the Server

Start the MCP server:

```bash
python youtube_api.py
```

## Available Tools

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

## Available Resources

### `youtube://status`

Checks if the YouTube API is configured correctly.

### `youtube://trending`

Gets the current trending videos on YouTube.

### `youtube://categories`

Gets a list of YouTube video categories.

## Extending the Server

This server can be extended with additional tools and resources by following the MCP server pattern. To add new functionality:

1. Add a new tool or resource method in `youtube_api.py`
2. Use the `@mcp.tool()` or `@mcp.resource()` decorators
3. Restart the server to apply changes

## Troubleshooting

- If you receive authentication errors, make sure your API key is set correctly
- Check the server logs for detailed error information
- Ensure your API key has the necessary permissions for the YouTube Data API v3

## License

N/A (Private)
