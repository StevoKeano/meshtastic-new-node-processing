import time
import subprocess
import os
import re
from datetime import datetime

# Configuration
PORT = '/dev/ttyACM0'  # Update this to your actual port
NODE_FILE = 'nodes.txt'  # File to store node IDs
LOG_FILE = 'traceroute_log.txt'  # File to log traceroute output

def get_nodes():
    """Fetch the current node list from the Meshtastic device."""
    try:
        command = f'python3 -m meshtastic --port {PORT} --info'
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        
        # Regular expression to find node IDs
        nodes = {}
        node_pattern = re.compile(r'\"!(\w+)\":\s*{')  # Matches node IDs like "!1c314db4"
        
        for line in result.stdout.splitlines():
            match = node_pattern.search(line)
            if match:
                node_id = f"!{match.group(1)}"
                nodes[node_id] = {}  # Initialize node entry
        return nodes.keys()  # Return only node IDs

    except subprocess.CalledProcessError as e:
        print(f"Error fetching nodes: {e.stderr}")
        return []

def load_existing_nodes():
    """Load existing node IDs from the node file."""
    if os.path.exists(NODE_FILE):
        with open(NODE_FILE, 'r') as f:
            return {line.strip() for line in f if line.strip()}
    return set()

def load_traceroute_log_nodes():
    """Load node IDs from the traceroute log file."""
    if os.path.exists(LOG_FILE):
        logged_nodes = set()
        with open(LOG_FILE, 'r') as f:
            for line in f:
                #print(len(line.split()))
                # Check for successful log entries
                if 'Traceroute output for' in line:
                   # print('# Extract node ID from successful log')
                   # print(line)
                    logged_node = line.split()[6].rstrip(':')  # Successful log format
                    logged_nodes.add(logged_node)
                # Check for unsuccessful log entries
                elif len(line.split()) > 3 and line.split()[3].startswith('!'):
                    # Extract node ID from unsuccessful log')
                    logged_node = line.split()[3]  # Unsuccessful log format                    
                    logged_nodes.add(logged_node)
        return logged_nodes
    return set()

def token_exists_in_log(token, log_file='traceroute_log.txt'):
    """Check if the given token exists in the traceroute log file."""
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            for line in f:
                # Check for the token in both successful and unsuccessful log formats
                if token in line:
                    return False  # Token exists, return False
    return True  # Token does not exist, return True

def save_node(node_id):
    """Save a new node ID to the node file."""
    with open(NODE_FILE, 'a') as f:
        f.write(f"{node_id}\r\n")  # CRLF at end of line

def issue_traceroute(node_id):
    """Run traceroute on the new node and log the output."""
    try:
        command = f"python3 -m meshtastic --traceroute '{node_id}'"
        
        # Using subprocess.run with shell=True to execute the command
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)

        # Extract the relevant traceroute line
        traceroute_line = None
        for line in result.stdout.splitlines():
            if ' --> ' in line:  # Check for the traceroute output format
                traceroute_line = line.strip()
                break

        # If we found a valid traceroute line, log it
        if traceroute_line:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get the current date and time
            log_entry = f"{timestamp} - Traceroute output for {node_id}: {traceroute_line}"
            print(log_entry)  # Print to the screen
            with open(LOG_FILE, 'a') as log_file:
                log_file.write(f"{log_entry}\r\n")  # Log the entry with timestamp
            return True  # Indicate success
        else:
            print(f"No valid traceroute output for {node_id}.")
            return False  # Indicate failure

    except subprocess.CalledProcessError as e:
        # Log the error message in the specified format with timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get the current date and time
        error_message = f"{timestamp} - {node_id} {e.stderr.strip()}"
        print(f"Error running traceroute for {node_id}: {error_message}")  # Print the error output
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f"{error_message}\r\n")  # Log the error message with timestamp
        return False  # Indicate failure

def main():
    """Main function to fetch nodes, check for new ones, and run traceroute."""
    while True:
        current_nodes = get_nodes()
        existing_nodes = load_existing_nodes()
        traceroute_log_nodes = load_traceroute_log_nodes()

        for node_id in current_nodes:
            if node_id in traceroute_log_nodes:
                print(f"Skipping node {node_id} as it's already in the traceroute log.")
            elif node_id not in existing_nodes:
                print(f"New node detected: {node_id}")
                # Run traceroute and check success
                traceroute_successful = issue_traceroute(node_id)
                if traceroute_successful:
                    save_node(node_id)  # Only save the node if traceroute was successful
        print('sleep 180 seconds from ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')  )
        # Sleep for 3 minutes (180 seconds)
        time.sleep(180)
    
if __name__ == "__main__":
    main()

