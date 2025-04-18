#!/usr/bin/env python3
import json
import re

# filepath: gap_analysis.py

def load_discovery_document():
    """Load the YouTube API discovery document."""
    with open("youtube-v3-discovery.json", "r") as f:
        return json.load(f)

def extract_api_methods(discovery_doc):
    """Extract all methods from the discovery document."""
    methods = {}
    
    # Process all resources and their methods
    for resource_name, resource_data in discovery_doc.get("resources", {}).items():
        for method_name, method_data in resource_data.get("methods", {}).items():
            # Create a key for this API method
            key = f"{resource_name}.{method_name}"
            # Get parameters for this method
            params = list(method_data.get("parameters", {}).keys())
            methods[key] = {
                "resource": resource_name,
                "method": method_name,
                "parameters": params
            }
    
    return methods

def find_implemented_methods():
    """Find methods implemented in the youtube_api.py file."""
    implemented = []
    
    # Read youtube_api.py file
    with open("youtube_api.py", "r") as f:
        content = f.read()
    
    # Find all @mcp.tool() functions
    tool_matches = re.findall(r'@mcp\.tool\(\).*?async def ([a-zA-Z0-9_]+)', content, re.DOTALL)
    
    # Find all @mcp.resource() declarations
    resource_matches = re.findall(r'@mcp\.resource\("([^"]+)"\)', content)
    
    # Create mappings between API methods and implemented functions
    # This mapping is created manually based on knowledge of the codebase
    method_to_function = {
        "search.list": "search_videos",
        "videos.list": "get_video_details",
        "channels.list": "get_channel_info",
        "playlistItems.list": "list_channel_videos",
        "playlists.list": "get_playlist_details",
        "commentThreads.list": "get_video_comments",
        "subscriptions.list": "get_channel_subscriptions",
        "videoCategories.list": "get_video_categories"  # Mapped to a resource
    }
    
    # Add all tools
    implemented.extend([(func, "tool") for func in tool_matches])
    
    # Add all resources
    implemented.extend([(path, "resource") for path in resource_matches])
    
    return implemented, method_to_function

def perform_gap_analysis():
    """Perform gap analysis between API methods and implementations."""
    # Load discovery document
    discovery_doc = load_discovery_document()
    
    # Extract API methods
    api_methods = extract_api_methods(discovery_doc)
    
    # Find implemented methods
    implemented, method_to_function = find_implemented_methods()
    
    # Display implemented methods
    print("Implemented Methods:")
    print("===================")
    for impl, impl_type in implemented:
        print(f"  - {impl} ({impl_type})")
    print()
    
    # Display mappings
    print("API Method Mappings:")
    print("===================")
    for api_method, function in method_to_function.items():
        print(f"  - {api_method} -> {function}")
    print()
    
    # Check which API methods are implemented
    implemented_methods = []
    not_implemented = []
    
    for method_key, method_info in api_methods.items():
        resource = method_info["resource"]
        method = method_info["method"]
        parameters = method_info["parameters"]
        
        # Check if this method is implemented based on our mapping
        if method_key in method_to_function:
            function_name = method_to_function[method_key]
            # Find the implementation type (tool or resource)
            impl_type = next((t for f, t in implemented if f == function_name), "Unknown")
            
            implemented_methods.append({
                "resource": resource,
                "method": method,
                "status": f"Implemented ({impl_type})",
                "parameters": parameters
            })
        else:
            not_implemented.append({
                "resource": resource,
                "method": method,
                "status": "Not Implemented",
                "parameters": parameters
            })
    
    # Print results
    print("Gap Analysis Results:")
    print("====================")
    print(f"{'Resource':<20} {'Method':<15} {'Status':<25} Parameters")
    print("-" * 80)
    
    # First show implemented methods
    for entry in implemented_methods:
        print(f"{entry['resource']:<20} {entry['method']:<15} {entry['status']:<25} {', '.join(entry['parameters'][:3])}{'...' if len(entry['parameters']) > 3 else ''}")
    
    # Then show not implemented methods (limited to conserve space)
    for entry in not_implemented[:20]:  # Show only first 20 not implemented
        print(f"{entry['resource']:<20} {entry['method']:<15} {entry['status']:<25} {', '.join(entry['parameters'][:3])}{'...' if len(entry['parameters']) > 3 else ''}")
    
    if len(not_implemented) > 20:
        print(f"... and {len(not_implemented) - 20} more not implemented methods")
    
    # Print summary
    total = len(implemented_methods) + len(not_implemented)
    percentage = len(implemented_methods) / total * 100 if total > 0 else 0
    print()
    print(f"Summary: {len(implemented_methods)}/{total} API methods implemented ({percentage:.1f}%)")

if __name__ == "__main__":
    perform_gap_analysis()
