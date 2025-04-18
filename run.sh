#!/bin/bash

# exit immediately if a command exits with a non-zero status
set -e

# Set colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}YouTube Data API MCP Server Setup and Run Script${NC}\n"

# Check if Python is installed
if ! command -v python3&> /dev/null; then
    echo -e "${RED}Error: Python is not installed. Please install Python 3 to continue.${NC}"
    exit 1
fi

# Check if uv is installed, if not install it
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}Installing uv package manager...${NC}"
    curl -sSf https://astral.sh/uv/install.sh | bash
    # Add uv to the current PATH
    export PATH="$HOME/.cargo/bin:$PATH"
    echo -e "${GREEN}uv installed.${NC}"
else
    echo -e "${GREEN}uv is already installed.${NC}"
fi

# Check if .venv directory exists, if not create it
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment with uv...${NC}"
    uv venv .venv
    echo -e "${GREEN}Virtual environment created.${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate
echo -e "${GREEN}Virtual environment activated.${NC}"

# Install dependencies with uv
echo -e "${YELLOW}Installing dependencies with uv...${NC}"
uv pip install -r requirements.txt
echo -e "${GREEN}Dependencies installed.${NC}"

# Check if API key is set
if [ -z "$YOUTUBE_API_KEY" ]; then
    echo -e "${YELLOW}YOUTUBE_API_KEY environment variable is not set.${NC}"
    read -p "Do you want to set it now? (y/n): " SET_KEY
    
    if [[ $SET_KEY == "y" || $SET_KEY == "Y" ]]; then
        read -p "Enter your YouTube API key: " API_KEY
        export YOUTUBE_API_KEY=$API_KEY
        echo -e "${GREEN}API key set for this session.${NC}"
        echo -e "${YELLOW}Note: To set the API key permanently, add the following to your shell configuration:${NC}"
        echo -e "export YOUTUBE_API_KEY=your-api-key-here"
    else
        echo -e "${RED}Warning: The server requires a YouTube API key to function.${NC}"
    fi
else
    echo -e "${GREEN}YouTube API key is set.${NC}"
fi

# Run the server
echo -e "\n${YELLOW}Starting YouTube Data API MCP server...${NC}"
python youtube_api.py

# Deactivate virtual environment on exit
echo -e "${YELLOW}Deactivating virtual environment...${NC}"
deactivate
echo -e "${GREEN}Done.${NC}"