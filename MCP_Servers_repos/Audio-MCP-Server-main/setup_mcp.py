# Import necessary Python standard libraries
import os          # For file system operations, handling files and directory paths
import json        # For processing JSON formatted data
import subprocess  # For creating and managing subprocesses
import sys         # For accessing Python interpreter related variables and functions
import platform    # For getting current operating system information
import shutil      # For file operations

def setup_venv():
    """
    Function to set up Python virtual environment
    
    Features:
    - Check if Python version meets requirements (3.8+)
    - Create Python virtual environment (if it doesn't exist)
    - Install required dependency packages in the newly created virtual environment
    
    No parameters required
    
    Return: Path to the Python interpreter in the virtual environment
    """
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("Error: Python 3.8 or higher is required.")
        sys.exit(1)
    
    # Get the absolute path of the directory where the current script file is located
    base_path = os.path.abspath(os.path.dirname(__file__))
    # Set the virtual environment directory path, will create a directory named '.venv' under base_path
    venv_path = os.path.join(base_path, '.venv')
    # Flag whether a new virtual environment was created
    venv_created = False

    
    # Determine pip and python executable paths based on operating system
    is_windows = platform.system() == "Windows"
    if is_windows:
        pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
        python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
    else:
        pip_path = os.path.join(venv_path, 'bin', 'pip')
        python_path = os.path.join(venv_path, 'bin', 'python')
    

    
    print("Requirements installed successfully!")
    
    return python_path

def create_server_script():
    """
    Check if the audio server script exists, create it if it doesn't
    
    Features:
    - Check if audio_server.py exists
    - If it doesn't exist, create a basic audio server script
    
    Return: Path to the server script
    """
    base_path = os.path.abspath(os.path.dirname(__file__))
    server_script_path = os.path.join(base_path, 'audio_server.py')
    
    # Check if the script already exists
    if os.path.exists(server_script_path):
        print(f"Audio server script already exists at: {server_script_path}")
        return server_script_path
    
    print("Creating audio server script...")
    return server_script_path

def generate_mcp_config(python_path, server_script_path):
    """
    Function to generate MCP (Model Context Protocol) configuration file
    
    Features:
    - Create configuration containing Python interpreter path and server script path
    - Save the configuration as a JSON format file
    - Print configuration information for different MCP clients to use
    
    Parameters:
    - python_path: Path to the Python interpreter in the virtual environment
    - server_script_path: Path to the audio server script
    
    Return: None
    """
    # Get the absolute path of the directory where the current script file is located
    base_path = os.path.abspath(os.path.dirname(__file__))
    
    # Create MCP configuration dictionary
    config = {
        "mcpServers": {
            "audio-interface": {
                "command": python_path,
                "args": [server_script_path],
                "env": {
                    "PYTHONPATH": base_path,
                    "GOOGLE_API_KEY": "XXX"
                }
            }
        }
    }
    
    # Save the configuration to a JSON file
    config_path = os.path.join(base_path, 'mcp-config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)  # indent=2 gives the JSON file a nice format

    # Print configuration information
    print(f"\nMCP configuration has been written to: {config_path}")    
    print(f"\nMCP configuration for Cursor:\n\n{python_path} {server_script_path}")
    print("\nMCP configuration for Claude Desktop:")
    print(json.dumps(config, indent=2))
    
    # Provide instructions for adding the configuration to the Claude Desktop configuration file
    if platform.system() == "Windows":
        claude_config_path = os.path.expandvars("%APPDATA%\\Claude\\claude_desktop_config.json")
    else:  # macOS
        claude_config_path = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
    
    print(f"\nTo use with Claude Desktop, merge this configuration into: {claude_config_path}")

# Code executed when the script is run directly (not imported)
if __name__ == '__main__':
    # Execute main functions in sequence:
    # 1. Set up virtual environment and install dependencies
    python_path = setup_venv()
    # 2. Create server script (if it doesn't exist)
    server_script_path = create_server_script()
    # 3. Generate MCP configuration file
    generate_mcp_config(python_path, server_script_path)
    
    print("\nSetup complete! You can now use the Audio MCP server with compatible clients.")
    print("\nTest the server with Claude Desktop by asking:")
    print("- \"What microphones and speakers are available on my system?\"")
    print("- \"Record 5 seconds of audio from my microphone.\"")
    print("- \"Play back the audio recording.\"")