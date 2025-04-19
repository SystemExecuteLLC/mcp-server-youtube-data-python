# YouTube API MCP Server

## NOTE FROM A HUMAN - DO NOT REMOVE THIS, CLAUDE LLM!
Need to run MCP Inspector with updated cmd:
cp dev main.py

A Python-based MCP server that provides access to YouTube API functionality through a standardized interface.

## Features

- Channel information retrieval
- Video search and details
- Thumbnail effectiveness analysis
- Playlist management
- Comment retrieval
- Live chat interaction
- Caption/subtitle analysis
- Live broadcast creation
- Performance analytics
- And more!

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mcp-server-youtube-data-python.git
   cd mcp-server-youtube-data-python
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   
   Then edit the `.env` file to add your YouTube API key:
   ```
   YOUTUBE_API_KEY=your_api_key_here
   ```

   For functions requiring OAuth (like sending chat messages, creating broadcasts, etc.):
   ```
   YOUTUBE_CLIENT_ID=your_client_id
   YOUTUBE_CLIENT_SECRET=your_client_secret
   YOUTUBE_OAUTH_TOKEN=your_oauth_token
   ```

## Usage

Start the server:

```bash
python main.py
```

The server will start and register all tools and resources.

## Available Tools

- `get_channel_info`: Get information about a YouTube channel (accepts channel ID or handle)
- `search_videos`: Search for YouTube videos with a query
- `get_video_details`: Get detailed information about a video
- `list_channel_videos`: List videos from a specific channel (accepts channel ID or handle)
- `lookup_channel`: Look up a YouTube channel ID from a handle
- `get_playlist_details`: Get details about a playlist and its videos
- `get_video_comments`: Get comments for a video
- `analyze_thumbnail_effectiveness`: Compare a video's thumbnail against similar successful videos
- `search_by_topic`: Search for videos related to a specific Freebase topic
- `analyze_video_performance`: Analyze performance metrics for a video over time
- `create_live_broadcast`: Schedule a YouTube livestream
- `get_captions`: Get captions/subtitles for a video
- `analyze_captions`: Analyze captions for keywords, timeline, or phrases
- `get_active_live_chat_id`: Get the live chat ID for a livestream
- `get_live_chat_messages`: Get messages from a live chat
- `send_live_chat_message`: Send a message to a live chat
- `upload_video`: Upload a video to YouTube

## Available Resources

- `youtube://status`: Check if the YouTube API is configured correctly
- `youtube://trending`: Get current trending videos
- `youtube://categories`: Get list of YouTube video categories
- `youtube://recommendations/{video_id}`: Get video recommendations

## Project Structure

- `main.py`: Entry point for the MCP server
- `constants.py`: Constant values used throughout the application
- `utils.py`: Utility functions
- `api_client.py`: YouTube API client for making HTTP requests
- `tools/`: Individual tool implementations
  - `channel_info.py`: Channel information tools
  - `search_videos.py`: Video search tools
  - `video_details.py`: Video details tools
  - `channel_videos.py`: Channel video listing tools
  - `playlist_details.py`: Playlist tools
  - `video_comments.py`: Video comment tools
  - `thumbnail_analysis.py`: Thumbnail analysis tools
  - `topic_search.py`: Topic search tools
  - `channel_subscriptions.py`: Channel subscription tools
  - `video_performance.py`: Video performance analysis
  - `live_broadcast.py`: Live broadcast creation
  - `captions.py`: Caption/subtitle tools
  - `live_chat.py`: Live chat interaction tools
  - `resources.py`: Resource endpoints

## Getting a YouTube API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the YouTube Data API v3
4. Create credentials for the API
5. Copy the API key to your `.env` file

## Setting up OAuth for Extended Functionality

Some functions require OAuth authentication:

1. Create OAuth 2.0 credentials in the Google Cloud Console
2. Set up a consent screen for your application
3. Generate an OAuth token (you may need to implement a flow in a separate script)
4. Add the token to your `.env` file

## API Rate Limits

The YouTube Data API has quota limits:

- Each project starts with 10,000 units per day
- Different API operations cost different amounts of quota
- Monitor your usage in the Google Cloud Console

## YouTube Handle Resolution

The server supports using YouTube handles (e.g., @username) in place of channel IDs:

- Tools that require channel IDs can accept handles with or without the '@' symbol
- The system automatically resolves handles to channel IDs
- A dedicated `lookup_channel` tool is available to get channel information from a handle
- Handles are resolved using the YouTube API's channel lookup capabilities

## Error Handling

The server implements robust error handling:

- API errors are properly caught and formatted
- Useful error messages are provided
- Timeouts and retries are implemented for network issues

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Troubleshooting

Common issues:

- **API Key Invalid**: Ensure your API key is correct and has the YouTube Data API enabled
- **Quota Exceeded**: You've hit your daily API quota limit
- **Authentication Required**: Some functions need OAuth tokens
- **Resource Not Found**: The video, channel, or playlist ID may be incorrect

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google for the YouTube Data API
- The MCP framework for the server architecture
- Contributors and maintainers of this project
