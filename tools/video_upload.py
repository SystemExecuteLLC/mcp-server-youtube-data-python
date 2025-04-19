"""
Tool for uploading videos to YouTube.
"""

import os
import sys
import mimetypes
from typing import Any, Dict, List, Optional

# Import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_client import make_youtube_request
from utils import get_api_key

async def upload_video(file_path: str, title: str, description: str, privacy_status: str = "private", 
                      tags: List[str] = None, category_id: str = "22", notify_subscribers: bool = True, 
                      language: str = "en", location_latitude: float = None, location_longitude: float = None, 
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
    
    Returns:
        Dict containing result or error message
    """
    # Validate input parameters
    if not file_path or not title or not description:
        return {"error": "File path, title, and description are required."}
    
    if privacy_status not in ["private", "public", "unlisted"]:
        return {"error": "Privacy status must be 'private', 'public', or 'unlisted'."}
    
    # Check if file exists
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    
    # Get file size and verify it's not too large (YouTube limits apply)
    file_size = os.path.getsize(file_path)
    max_file_size = 128 * 1024 * 1024 * 1024  # 128GB is YouTube's max for verified accounts
    if file_size > max_file_size:
        return {"error": f"File is too large. YouTube's maximum is 128GB, file is {file_size / (1024*1024*1024):.2f}GB"}
    
    # Determine MIME type based on file extension
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
