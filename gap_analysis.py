import json
import ast

# filepath: gap_analysis.py

def parse_discovery_json():
    """Parse the YouTube v3 Discovery JSON file to extract resources, methods, and parameters."""
    discovery_file = "youtube-v3-discovery.json"  # Assumes the file is in the same directory
    with open(discovery_file, "r") as f:
        discovery = json.load(f)

    api_structure = {}
    for resource, details in discovery.get("resources", {}).items():
        api_structure[resource] = {}
        for method, method_details in details.get("methods", {}).items():
            parameters = list(method_details.get("parameters", {}).keys())
            api_structure[resource][method] = parameters
    return api_structure


def parse_youtube_api_file():
    """Parse the youtube_api.py file to extract implemented functions."""
    api_file = "youtube_api.py"  # Assumes the file is in the same directory
    with open(api_file, "r") as f:
        tree = ast.parse(f.read())

    implemented_methods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            implemented_methods.add(node.name)
    return implemented_methods


def perform_gap_analysis(discovery_structure, implemented_methods):
    """Perform a gap analysis between the Discovery JSON and implemented methods."""
    gap_analysis = []

    for resource, methods in discovery_structure.items():
        for method, parameters in methods.items():
            function_name = f"{resource}_{method}"  # Assuming function names follow this pattern
            if function_name not in implemented_methods:
                gap_analysis.append({
                    "resource": resource,
                    "method": method,
                    "status": "Not Implemented",
                    "missing_parameters": parameters
                })
            else:
                gap_analysis.append({
                    "resource": resource,
                    "method": method,
                    "status": "Implemented",
                    "missing_parameters": []
                })

    return gap_analysis


def print_gap_analysis(gap_analysis):
    """Print the gap analysis in a readable format."""
    print(f"{'Resource':<15} {'Method':<15} {'Status':<20} Missing Parameters")
    print("-" * 60)
    for entry in gap_analysis:
        resource = entry["resource"]
        method = entry["method"]
        status = entry["status"]
        missing_params = ", ".join(entry["missing_parameters"])
        print(f"{resource:<15} {method:<15} {status:<20} {missing_params}")


if __name__ == "__main__":
    # Parse the Discovery JSON and youtube_api.py
    discovery_structure = parse_discovery_json()
    implemented_methods = parse_youtube_api_file()

    # Perform the gap analysis
    gap_analysis = perform_gap_analysis(discovery_structure, implemented_methods)

    # Print the results
    print_gap_analysis(gap_analysis)