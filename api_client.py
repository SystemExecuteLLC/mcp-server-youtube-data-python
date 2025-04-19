"""
YouTube API client handling HTTP requests and response processing.
"""

import sys
import httpx
from typing import Any, Dict, Optional

from constants import YOUTUBE_API_BASE, USER_AGENT
from utils import get_api_key

async def make_youtube_request(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make a request to the YouTube API with proper error handling.
    
    Args:
        endpoint: The YouTube API endpoint (e.g., "videos", "search")
        params: Dictionary of query parameters
    
    Returns:
        Dict containing API response or error information
    """
    if params is None:
        params = {}
    
    # Add API key to params
    api_key = get_api_key()
    if not api_key:
        print("Error: YouTube API key not available", file=sys.stderr)
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
            
            # Log the raw response content for debugging
            print(f"Response content: {response.text[:500]}", file=sys.stderr)  # First 500 chars
            
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

async def make_youtube_post_request(endpoint: str, data: Dict[str, Any], params: Dict[str, Any] = None, oauth_token: str = None) -> Dict[str, Any]:
    """Make a POST request to the YouTube API.
    
    Args:
        endpoint: The YouTube API endpoint
        data: The data to send in the POST request
        params: Dictionary of query parameters
        oauth_token: OAuth token for authorization (if required)
    
    Returns:
        Dict containing API response or error information
    """
    if params is None:
        params = {}
    
    # Add API key to params
    api_key = get_api_key()
    if not api_key:
        print("Error: YouTube API key not available", file=sys.stderr)
        return {"error": "YouTube API key not available"}
    
    params["key"] = api_key
    
    url = f"{YOUTUBE_API_BASE}/{endpoint}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Add OAuth token if provided
    if oauth_token:
        headers["Authorization"] = f"Bearer {oauth_token}"
    
    print(f"Making POST request to {url}", file=sys.stderr)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, params=params, json=data, timeout=30.0)
            print(f"Response status: {response.status_code}", file=sys.stderr)
            response.raise_for_status()
            try:
                json_data = response.json()
                print(f"DEBUG: Successfully parsed JSON response", file=sys.stderr)
                return json_data
            except Exception as e:
                print(f"Error parsing JSON from {url}: {str(e)}", file=sys.stderr)
                print(f"Response content: {response.text[:500]}", file=sys.stderr)
                return {"error": f"Error parsing JSON from {url}: {str(e)}"}
        except httpx.HTTPStatusError as e:
            print(f"HTTP error from {url}: {e.response.status_code} {e.response.reason_phrase}", file=sys.stderr)
            error_message = f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
            try:
                error_json = e.response.json()
                if "error" in error_json and "message" in error_json["error"]:
                    error_message = error_json["error"]["message"]
            except:
                pass
            return {"error": error_message}
        except Exception as e:
            print(f"Unexpected error in request to {url}: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Unexpected error: {str(e)}"}

async def get_oauth_credentials() -> Optional[str]:
    """Get OAuth credentials from environment variables.
    
    Returns:
        OAuth token or None if not available
    """
    import os
    
    oauth_token = os.getenv("YOUTUBE_OAUTH_TOKEN")
    if not oauth_token:
        print("WARNING: YOUTUBE_OAUTH_TOKEN environment variable not set", file=sys.stderr)
        return None
    
    return oauth_token
