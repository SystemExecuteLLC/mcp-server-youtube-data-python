"""
YouTube API audience demographics module.

This module implements the audience demographics functionality for the YouTube API wrapper.
It provides detailed information about a channel's audience including age, gender, geography,
device types, and traffic sources.
"""

from typing import Any, Dict, List
import os
import sys
from datetime import datetime, timedelta

async def get_audience_demographics(channel_id: str) -> Dict[str, Any]:
    """Get audience demographic information for a YouTube channel.
    
    This function retrieves demographic data about a channel's audience, including age groups,
    gender distribution, geographic location, and viewing device types. Requires OAuth.
    
    Args:
        channel_id: The ID of the YouTube channel to analyze
    """
    # Check for OAuth credentials
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    oauth_token = os.getenv("YOUTUBE_OAUTH_TOKEN")
    
    if not client_id or not client_secret or not oauth_token:
        return {"error": "OAuth credentials not available. Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, and YOUTUBE_OAUTH_TOKEN environment variables"}
    
    # Prepare headers with authorization
    headers = {
        "User-Agent": "youtube-mcp-server/1.0",
        "Accept": "application/json",
        "Authorization": f"Bearer {oauth_token}"
    }
    
    # First, validate the channel ID and get channel info
    from youtube_api import make_youtube_request, get_api_key
    
    channel_params = {
        "part": "snippet",
        "id": channel_id,
        "key": get_api_key()
    }
    
    channel_data = await make_youtube_request("channels", channel_params)
    
    if "error" in channel_data:
        return {"error": channel_data["error"]}
    
    if "items" not in channel_data or not channel_data["items"]:
        return {"error": "Channel not found or error fetching channel information."}
    
    channel_title = channel_data["items"][0].get("snippet", {}).get("title", "Unknown Channel")
    
    # Define the time range for demographics (last 90 days is typically recommended)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    
    # Set up analytics base URL
    analytics_base_url = "https://youtubeanalytics.googleapis.com/v2/reports"
    
    # Get demographic data by age and gender
    demo_params = {
        "ids": f"channel=={channel_id}",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "viewerPercentage",
        "dimensions": "ageGroup,gender",
        "sort": "gender,ageGroup"
    }
    
    # Get geographic data
    geo_params = {
        "ids": f"channel=={channel_id}",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage",
        "dimensions": "country",
        "sort": "-views",
        "maxResults": 25
    }
    
    # Get device and platform data
    device_params = {
        "ids": f"channel=={channel_id}",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,estimatedMinutesWatched",
        "dimensions": "deviceType",
        "sort": "-views"
    }
    
    # Get traffic source data
    traffic_params = {
        "ids": f"channel=={channel_id}",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,estimatedMinutesWatched",
        "dimensions": "insightTrafficSourceType",
        "sort": "-views"
    }
    
    import httpx
    
    async with httpx.AsyncClient() as client:
        try:
            # Get demographic data
            demo_response = await client.get(
                analytics_base_url, 
                headers=headers, 
                params=demo_params,
                timeout=30.0
            )
            demo_response.raise_for_status()
            demo_data = demo_response.json()
            
            # Get geographic data
            geo_response = await client.get(
                analytics_base_url, 
                headers=headers, 
                params=geo_params,
                timeout=30.0
            )
            geo_response.raise_for_status()
            geo_data = geo_response.json()
            
            # Get device type data
            device_response = await client.get(
                analytics_base_url, 
                headers=headers, 
                params=device_params,
                timeout=30.0
            )
            device_response.raise_for_status()
            device_data = device_response.json()
            
            # Get traffic source data
            traffic_response = await client.get(
                analytics_base_url, 
                headers=headers, 
                params=traffic_params,
                timeout=30.0
            )
            traffic_response.raise_for_status()
            traffic_data = traffic_response.json()
            
            # Process and format the results
            result = f"Audience Demographics for {channel_title} (ID: {channel_id})\n"
            result += f"Period: {start_date} to {end_date}\n\n"
            
            # Process age and gender data
            if "rows" in demo_data and demo_data["rows"]:
                result += "Age & Gender Distribution:\n"
                result += "-------------------------\n"
                
                # Group data by gender for formatting
                gender_data = {}
                gender_totals = {}
                
                for row in demo_data["rows"]:
                    age_group = row[0]
                    gender = row[1]
                    percentage = row[2]
                    
                    if gender not in gender_data:
                        gender_data[gender] = []
                        gender_totals[gender] = 0
                    
                    gender_data[gender].append((age_group, percentage))
                    gender_totals[gender] += percentage
                
                # If data might contain gender='GENDER_UNKNOWN', merge with other genders proportionally
                if "GENDER_UNKNOWN" in gender_totals:
                    unknown_total = gender_totals["GENDER_UNKNOWN"]
                    known_total = sum(v for k, v in gender_totals.items() if k != "GENDER_UNKNOWN")
                    
                    if known_total > 0:  # Avoid division by zero
                        for gender in gender_totals:
                            if gender != "GENDER_UNKNOWN":
                                ratio = gender_totals[gender] / known_total
                                gender_totals[gender] += unknown_total * ratio
                    
                    # Remove the unknown gender from outputs
                    if "GENDER_UNKNOWN" in gender_data:
                        del gender_data["GENDER_UNKNOWN"]
                    if "GENDER_UNKNOWN" in gender_totals:
                        del gender_totals["GENDER_UNKNOWN"]
                
                # Display gender distribution
                result += "Gender Distribution:\n"
                for gender, total in gender_totals.items():
                    gender_name = gender.replace("GENDER_", "").capitalize()
                    result += f"  {gender_name}: {total:.1f}%\n"
                
                # Display age distribution for each gender
                result += "\nAge Distribution:\n"
                
                # Get list of all age groups
                all_age_groups = set()
                for gender_rows in gender_data.values():
                    for age_group, _ in gender_rows:
                        all_age_groups.add(age_group)
                
                # Sort age groups for consistent output
                age_group_order = [
                    "AGE_13_17", "AGE_18_24", "AGE_25_34", "AGE_35_44", 
                    "AGE_45_54", "AGE_55_64", "AGE_65_"
                ]
                age_groups_sorted = sorted(all_age_groups, key=lambda x: age_group_order.index(x) if x in age_group_order else 999)
                
                # Create a mapping of friendly age group names
                age_group_names = {
                    "AGE_13_17": "13-17",
                    "AGE_18_24": "18-24",
                    "AGE_25_34": "25-34",
                    "AGE_35_44": "35-44",
                    "AGE_45_54": "45-54",
                    "AGE_55_64": "55-64",
                    "AGE_65_": "65+"
                }
                
                # Display results for each age group
                for age_group in age_groups_sorted:
                    age_name = age_group_names.get(age_group, age_group.replace("AGE_", "").replace("_", "-"))
                    result += f"  {age_name}: "
                    
                    total_for_age = 0
                    age_by_gender = {}
                    
                    for gender, rows in gender_data.items():
                        for ag, percentage in rows:
                            if ag == age_group:
                                gender_name = gender.replace("GENDER_", "").capitalize()
                                age_by_gender[gender_name] = percentage
                                total_for_age += percentage
                    
                    result += f"{total_for_age:.1f}% total "
                    gender_breakdown = ", ".join([f"{gender}: {pct:.1f}%" for gender, pct in age_by_gender.items()])
                    if gender_breakdown:
                        result += f"({gender_breakdown})"
                    result += "\n"
            else:
                result += "Age & Gender Data: Not available\n"
            
            # Process geographic data
            if "rows" in geo_data and geo_data["rows"]:
                result += "\nGeographic Distribution (Top 10 Countries):\n"
                result += "---------------------------------------\n"
                
                # Import country code to name mapping if available
                country_names = {}
                try:
                    import pycountry
                    country_names = {country.alpha_2: country.name for country in pycountry.countries}
                except ImportError:
                    # Fallback to a small subset of common country codes
                    country_names = {
                        "US": "United States", "GB": "United Kingdom", "CA": "Canada", 
                        "AU": "Australia", "DE": "Germany", "FR": "France", "IN": "India", 
                        "JP": "Japan", "BR": "Brazil", "MX": "Mexico", "ES": "Spain", 
                        "IT": "Italy", "NL": "Netherlands", "SE": "Sweden", "KR": "South Korea", 
                        "RU": "Russia", "CN": "China"
                    }
                
                # Get column headers
                col_headers = [h.get("name") for h in geo_data.get("columnHeaders", [])]
                view_index = col_headers.index("views") if "views" in col_headers else 1
                minutes_index = col_headers.index("estimatedMinutesWatched") if "estimatedMinutesWatched" in col_headers else 2
                
                # Calculate total views to get percentages
                total_views = sum(row[view_index] for row in geo_data["rows"])
                
                # Display top countries
                for i, row in enumerate(geo_data["rows"][:10], 1):
                    country_code = row[0]
                    views = row[view_index]
                    minutes = row[minutes_index]
                    
                    country_name = country_names.get(country_code, country_code)
                    view_percentage = (views / total_views) * 100 if total_views > 0 else 0
                    
                    result += f"{i}. {country_name} ({country_code}): {views:,} views ({view_percentage:.1f}%), {minutes:,} minutes watched\n"
            else:
                result += "\nGeographic Data: Not available\n"
            
            # Process device type data
            if "rows" in device_data and device_data["rows"]:
                result += "\nDevice Distribution:\n"
                result += "-------------------\n"
                
                # Get column headers
                col_headers = [h.get("name") for h in device_data.get("columnHeaders", [])]
                view_index = col_headers.index("views") if "views" in col_headers else 1
                minutes_index = col_headers.index("estimatedMinutesWatched") if "estimatedMinutesWatched" in col_headers else 2
                
                # Calculate total views for percentages
                total_views = sum(row[view_index] for row in device_data["rows"])
                total_minutes = sum(row[minutes_index] for row in device_data["rows"])
                
                # Create friendly names for device types
                device_names = {
                    "MOBILE": "Mobile Phone",
                    "TABLET": "Tablet",
                    "DESKTOP": "Desktop",
                    "GAME_CONSOLE": "Game Console",
                    "CONNECTED_TV": "Smart TV",
                    "UNKNOWN_PLATFORM": "Other Devices"
                }
                
                # Display device distribution
                for row in device_data["rows"]:
                    device_type = row[0]
                    views = row[view_index]
                    minutes = row[minutes_index]
                    
                    device_display_name = device_names.get(device_type, device_type)
                    view_percentage = (views / total_views) * 100 if total_views > 0 else 0
                    minutes_percentage = (minutes / total_minutes) * 100 if total_minutes > 0 else 0
                    
                    result += f"{device_display_name}: {views:,} views ({view_percentage:.1f}%), {minutes:,} minutes watched ({minutes_percentage:.1f}%)\n"
            else:
                result += "\nDevice Distribution: Not available\n"
            
            # Process traffic source data
            if "rows" in traffic_data and traffic_data["rows"]:
                result += "\nTraffic Sources:\n"
                result += "--------------\n"
                
                # Get column headers
                col_headers = [h.get("name") for h in traffic_data.get("columnHeaders", [])]
                view_index = col_headers.index("views") if "views" in col_headers else 1
                minutes_index = col_headers.index("estimatedMinutesWatched") if "estimatedMinutesWatched" in col_headers else 2
                
                # Calculate total views for percentages
                total_views = sum(row[view_index] for row in traffic_data["rows"])
                
                # Create friendly names for traffic sources
                source_names = {
                    "ADVERTISING": "Paid Advertising",
                    "ANNOTATION": "Annotations",
                    "EXTERNAL": "External Websites",
                    "PLAYLIST": "Playlists",
                    "PROMOTED": "Promoted Content",
                    "NOTIFICATION": "Notifications",
                    "RELATED_VIDEO": "Related Videos",
                    "SUBSCRIBER": "Subscriber Feed",
                    "SOCIAL": "Social Media",
                    "CHANNEL": "Channel Page",
                    "YOUTUBE_SEARCH": "YouTube Search",
                    "GOOGLE_SEARCH": "Google Search",
                    "SUGGESTED_VIDEO": "Suggested Videos",
                    "OTHER": "Other Sources",
                    "NO_LINK_EMBEDDED": "Embedded (No Link)",
                    "YT_SEARCH": "YouTube Search"
                }
                
                # Display traffic sources
                for row in traffic_data["rows"]:
                    source_type = row[0]
                    views = row[view_index]
                    minutes = row[minutes_index]
                    
                    source_display_name = source_names.get(source_type, source_type.replace("_", " ").title())
                    view_percentage = (views / total_views) * 100 if total_views > 0 else 0
                    
                    result += f"{source_display_name}: {views:,} views ({view_percentage:.1f}%), {minutes:,} minutes watched\n"
            else:
                result += "\nTraffic Sources: Not available\n"
            
            # Add insights and recommendations
            result += "\nAudience Insights:\n"
            result += "----------------\n"
            
            # Try to generate age and gender insights
            try:
                if "rows" in demo_data and demo_data["rows"]:
                    # Find primary age group
                    age_totals = {}
                    for row in demo_data["rows"]:
                        age_group = row[0]
                        percentage = row[2]
                        
                        if age_group not in age_totals:
                            age_totals[age_group] = 0
                        
                        age_totals[age_group] += percentage
                    
                    # Find top age group
                    top_age = max(age_totals.items(), key=lambda x: x[1]) if age_totals else None
                    age_group_names = {
                        "AGE_13_17": "13-17",
                        "AGE_18_24": "18-24",
                        "AGE_25_34": "25-34",
                        "AGE_35_44": "35-44",
                        "AGE_45_54": "45-54",
                        "AGE_55_64": "55-64",
                        "AGE_65_": "65+"
                    }
                    
                    if top_age:
                        top_age_name = age_group_names.get(top_age[0], top_age[0].replace("AGE_", "").replace("_", "-"))
                        result += f"- Primary age demographic: {top_age_name} ({top_age[1]:.1f}% of viewers)\n"
                    
                    # Find primary gender
                    primary_gender = max(gender_totals.items(), key=lambda x: x[1]) if 'gender_totals' in locals() and gender_totals else None
                    if primary_gender:
                        gender_name = primary_gender[0].replace("GENDER_", "").capitalize()
                        result += f"- Gender breakdown: {gender_name} viewers represent {primary_gender[1]:.1f}% of your audience\n"
            except Exception:
                pass
            
            # Try to generate geographic insights
            try:
                if "rows" in geo_data and geo_data["rows"] and len(geo_data["rows"]) > 0:
                    top_country = geo_data["rows"][0]
                    country_code = top_country[0]
                    country_name = country_names.get(country_code, country_code)
                    views = top_country[view_index]
                    view_percentage = (views / total_views) * 100 if total_views > 0 else 0
                    
                    result += f"- Geographic concentration: {country_name} is your top audience location ({view_percentage:.1f}% of views)\n"
                    
                    # Check audience diversity
                    num_countries = len(geo_data["rows"])
                    top3_percentage = sum((row[view_index] / total_views) * 100 for row in geo_data["rows"][:3]) if total_views > 0 else 0
                    
                    if num_countries > 10 and top3_percentage < 60:
                        result += f"- Your audience is geographically diverse (spread across {num_countries} countries)\n"
                    elif num_countries > 1 and top3_percentage > 80:
                        result += f"- Your audience is concentrated in a few key regions (top 3 countries represent {top3_percentage:.1f}% of views)\n"
            except Exception:
                pass
                
            # Try to generate device insights
            try:
                if "rows" in device_data and device_data["rows"]:
                    # Build device breakdown
                    device_breakdown = {}
                    for row in device_data["rows"]:
                        device_type = row[0]
                        views = row[view_index]
                        device_name = device_names.get(device_type, device_type)
                        view_percentage = (views / total_views) * 100 if total_views > 0 else 0
                        device_breakdown[device_name] = view_percentage
                    
                    # Check if mobile-heavy
                    mobile_percentage = device_breakdown.get("Mobile Phone", 0) + device_breakdown.get("Tablet", 0)
                    if mobile_percentage > 60:
                        result += f"- Your audience primarily watches on mobile devices ({mobile_percentage:.1f}% of views)\n"
                    elif device_breakdown.get("Connected TV", 0) > 40:
                        result += f"- Your audience has high TV viewership ({device_breakdown.get('Connected TV', 0):.1f}% of views)\n"
            except Exception:
                pass
                
            # Try to generate traffic source insights
            try:
                if "rows" in traffic_data and traffic_data["rows"]:
                    # Analyze traffic sources
                    source_breakdown = {}
                    for row in traffic_data["rows"]:
                        source_type = row[0]
                        views = row[view_index]
                        source_name = source_names.get(source_type, source_type.replace("_", " ").title())
                        view_percentage = (views / total_views) * 100 if total_views > 0 else 0
                        source_breakdown[source_name] = view_percentage
                    
                    # Find top traffic source
                    top_source = max(source_breakdown.items(), key=lambda x: x[1]) if source_breakdown else None
                    if top_source:
                        result += f"- Traffic pattern: {top_source[0]} is your primary traffic source ({top_source[1]:.1f}% of views)\n"
                        
                    # Check for search dependency
                    search_percentage = source_breakdown.get("YouTube Search", 0) + source_breakdown.get("Google Search", 0)
                    if search_percentage > 30:
                        result += f"- Your channel relies heavily on search traffic ({search_percentage:.1f}% of views)\n"
                        
                    # Check for subscriber activity
                    subscriber_percentage = source_breakdown.get("Subscriber Feed", 0) + source_breakdown.get("Notifications", 0)
                    if subscriber_percentage < 15 and source_breakdown.get("Subscriber Feed", 0) > 0:
                        result += f"- Your subscribers account for only {subscriber_percentage:.1f}% of your views - consider encouraging more engagement\n"
                    elif subscriber_percentage > 50:
                        result += f"- Your channel has strong subscriber engagement ({subscriber_percentage:.1f}% of views)\n"
            except Exception:
                pass
            
            result += "\nNote: For more detailed demographic data, visit YouTube Studio.\n"
            
            return {"result": result}
        
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
            try:
                error_json = e.response.json()
                if "error" in error_json and "message" in error_json["error"]:
                    error_message = error_json["error"]["message"]
            except:
                pass
                
            return {"error": f"Failed to retrieve audience demographics: {error_message}"}
            
        except Exception as e:
            return {"error": f"Unexpected error retrieving audience demographics: {str(e)}"}
