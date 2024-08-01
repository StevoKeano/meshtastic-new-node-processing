import subprocess
import serial.tools.list_ports
import sys
import json
import os
import shlex
from datetime import datetime, timedelta

timeoutSeconds = 10
NODE_FILE =  os.path.join(os.path.dirname(__file__), 'nodes.txt')  # File to store node IDs
LOG_FILE = os.path.join(os.path.dirname(__file__), 'traceroute_log.txt')  # File to log traceroute output
yourInviteString = "https://discord.gg/cpDFj345"  # Update this or you'll be sending MY NAME to everyone!'
welcomeMsg =  f"Welcome to the mesh! Join us on the AustinMesh discord chat: {yourInviteString}" # default value...

import os
import json

# Global variable for the welcome message
welcomeMsg = "Welcome to the mesh!"  # Default value

def load_settings():
    """Load settings from the settings.json file."""
    global welcomeMsg
    try:
        # Construct the path to settings.json relative to this file
        settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
        with open(settings_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        # Return default settings if the file does not exist
        return {"welcome_message": welcomeMsg}

def update_welcome_message(change="y"):
    """Update the welcome message in settings.json."""
    global welcomeMsg
    settings = load_settings()
    current_message = settings.get('welcome_message', welcomeMsg)    

    if change.lower() == 'y':
        new_message = input("Enter the new welcome message: ")
        settings['welcome_message'] = new_message
        
        # Construct the path to settings.json for saving
        settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
        with open(settings_path, 'w') as file:
            json.dump(settings, file, indent=2)        
        print("Welcome message updated successfully!")
        return new_message
    else:
        print("Welcome message remains unchanged.")
        return current_message

if __name__ == "__main__":
    update_welcome_message()



def check_meshtastic_port(port):
    command = f'{sys.executable} -m meshtastic --port {port} --info'
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, timeout=timeoutSeconds)
        output_lines = result.stdout.strip().split('\n')
        if output_lines and output_lines[-1].startswith("Complete URL"):
            print(f"Meshtastic device found on {port}")
            return True
    except subprocess.CalledProcessError as e:
        print(f"Error running Meshtastic command on {port}: {e}")
    except subprocess.TimeoutExpired:
        print(f"Timeout on {port}")
    except Exception as e:
        print(f"Unexpected error on {port}: {e}")
    return False

def check_meshtastic_ip(ip_address):
    command = [sys.executable, '-m', 'meshtastic', '--host', ip_address, '--info']
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeoutSeconds)
        output_lines = result.stdout.strip().split('\n')
        if output_lines and output_lines[-1].startswith("Complete URL"):
            print(f"Meshtastic device found at {ip_address}")
            return True
    except subprocess.CalledProcessError as e:
        print(f"Error connecting to Meshtastic device at {ip_address}: {e}")
    except subprocess.TimeoutExpired:
        print(f"Timeout connecting to {ip_address}")
    except Exception as e:
        print(f"Unexpected error connecting to {ip_address}: {e}")
    return False

def sendMsg(node_id, message, connection_string):
    """Send a message to a specific node using Meshtastic CLI."""
    # Split the connection string into parts
    conn_parts = shlex.split(connection_string)
    
    # Construct the command as a list
    command = [sys.executable, '-m', 'meshtastic'] + conn_parts + ['--sendtext', message, '--dest', node_id]
    
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error sending message to {node_id}: {e}")
        print(f"Command output: {e.stderr}")

'''# Example usage
if __name__ == "__main__":
    node_id = "!abcdef12"  # Replace with actual node ID
    message = "Hello, Meshtastic!"
    connection_string = "--host 192.168.1.100"  # Or "--port COM3" for serial connection
    sendMsg(node_id, message, connection_string)
'''

def load_existing_nodes():
    """Load existing node IDs from the node file."""
    nodes = set()
    if os.path.exists(NODE_FILE):
        with open(NODE_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    node_id, *rest = line.split(',')
                    nodes.add(node_id)
    return nodes

def load_traceroute_log_nodes():
    """Load node IDs from the traceroute log file."""
    logged_nodes = set()
    
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            for line in f:
                # Check for successful log entries
                if 'Traceroute output for' in line:
                    logged_node = line.split()[6].rstrip(':')  # Successful log format
                    logged_nodes.add(logged_node)
                # Check for unsuccessful log entries
                elif len(line.split()) > 3 and line.split()[3].startswith('!'):
                    logged_node = line.split()[3]  # Unsuccessful log format                    
                    logged_nodes.add(logged_node)
    
    return logged_nodes

'''# Example usage
if __name__ == "__main__":
    traceroute_nodes = load_traceroute_log_nodes()
    print(f"Loaded traceroute nodes: {traceroute_nodes}")
'''

def save_node(node_id, last_heard=None, user=None, device_metrics=None, seen_time=None):
    """Save a new node ID along with lastHeard, user, and deviceMetrics to the node file."""
    # Prepare the output line with the provided data
    output_line = f"{node_id},{last_heard},{user},{device_metrics},{seen_time}\n"  # Use LF for line ending
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(NODE_FILE), exist_ok=True)

    # Append the node information to the file
    with open(NODE_FILE, 'a') as f:
        f.write(output_line)

'''# Example usage
if __name__ == "__main__":
    save_node("!abcdef12", "2024-07-31T12:00:00Z", "User1", "DeviceMetrics1", "2024-07-31T12:00:00Z")
'''

# Define the global variable LOG_FILE
python_executable = sys.executable  # Ensure this is set correctly

def issue_traceroute(node_id, connection_string):
    """Run traceroute on the new node and log the output."""
    try:
        # Prepare the command with the connection string
        if connection_string.startswith('--host'):
            parts = connection_string.split()
            protocol = parts[0]
            ip = parts[1]
            command = [python_executable, '-m', 'meshtastic', protocol, ip, '--traceroute', node_id]  # remote IP
        else:
            command = [python_executable, '-m', 'meshtastic', '--traceroute', node_id]  # USB Port

        print(f'Sending traceroute request to {node_id} (this could take a while)')

        # Run the traceroute command
        result = subprocess.run(command, check=True, capture_output=True, text=True)

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
                log_file.write(f"{log_entry}\n")  # Log the entry with timestamp
            return True  # Indicate success
        else:
            print(f"No valid traceroute output for {node_id}.")
            with open(LOG_FILE, 'a') as log_file:
                log_file.write(f"No valid traceroute output for {node_id}.\n")  # Log the entry
            return False  # Indicate failure

    except subprocess.CalledProcessError as e:
        # Log the error message in the specified format with timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get the current date and time
        error_message = f"{timestamp} - {node_id} {e.stderr.strip()}"
        print(f"Error running traceroute for {node_id}: {error_message}")  # Print the error output
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f"{error_message}\n")  # Log the error message with timestamp
        return False  # Indicate failure

    except FileNotFoundError:
        print(f"The specified Python executable was not found: {python_executable}")
        return False  # Indicate failure

    except Exception as e:
        print(f"An unexpected error occurred while running traceroute for {node_id}: {str(e)}")
        return False  # Indicate failure



def find_meshtastic_port():
    """Scan for Meshtastic device on COM ports or prompt for IP address."""
    ports = sorted(serial.tools.list_ports.comports(), key=lambda x: x.device, reverse=True)
    
    print("Scanning for Meshtastic device...")
    for port in ports:
        print(f"\nChecking port: {port.device}")
        if check_meshtastic_port(port.device):
            return port.device

    print("No Meshtastic device found on COM ports.")
    
    # If no COM ports were found, ask for IP address
    ip_address = input("Enter IP address of the Meshtastic device (or press Enter to exit): ").strip()
    
    if ip_address:
        if check_meshtastic_ip(ip_address):
            return f"--host {ip_address}"
    
    return None

'''# Example usage
if __name__ == "__main__":
    meshtastic_port = find_meshtastic_port()
    if meshtastic_port:
        print(f"Meshtastic device found at: {meshtastic_port}")
    else:
        print("No Meshtastic device found.")
'''

# Define the timeout duration globally
timeoutSeconds = 10  # Adjust as needed

def check_meshtastic_port(port):
    """Check if a Meshtastic device is connected at the specified port."""
    command = [sys.executable, '-m', 'meshtastic', '--port', port, '--info']
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeoutSeconds)
        output_lines = result.stdout.strip().split('\n')
        if output_lines and output_lines[-1].startswith("Complete URL"):
            print(f"Meshtastic device found on {port}")
            return True
    except subprocess.CalledProcessError as e:
        print(f"Error running Meshtastic command on {port}: {e}")
    except subprocess.TimeoutExpired:
        print(f"Timeout on {port}")
    except Exception as e:
        print(f"Unexpected error on {port}: {e}")
    
    return False

'''# Example usage
if __name__ == "__main__":
    test_port = "COM3"  # Replace with the actual port to test
    if check_meshtastic_port(test_port):
        print("Device is connected.")
    else:
        print("Device not found.")
'''

# Define the timeout duration globally
timeoutSeconds = 10  # Adjust as needed

def check_meshtastic_ip(ip_address):
    """Check if a Meshtastic device is connected at the specified IP address."""
    command = [sys.executable, '-m', 'meshtastic', '--host', ip_address, '--info']
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeoutSeconds)
        output_lines = result.stdout.strip().split('\n')
        if output_lines and output_lines[-1].startswith("Complete URL"):
            print(f"Meshtastic device found at {ip_address}")
            return True
    except subprocess.CalledProcessError as e:
        print(f"Error connecting to Meshtastic device at {ip_address}: {e}")
    except subprocess.TimeoutExpired:
        print(f"Timeout connecting to {ip_address}")
    except Exception as e:
        print(f"Unexpected error connecting to {ip_address}: {e}")
    
    return False

'''# Example usage
if __name__ == "__main__":
    test_ip = "192.168.1.100"  # Replace with the actual IP address to test
    if check_meshtastic_ip(test_ip):
        print("Device is connected.")
    else:
        print("Device not found.")
'''

def get_nodes_info(connection_string):
    """Get the list of nodes and their info using Meshtastic CLI."""
    command = [sys.executable, '-m', 'meshtastic'] + connection_string.split() + ['--info']
    nodes_info = []  # Initialize nodes_info at the start

    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=10)
        
        # Attempt to parse the output as JSON
        start_index = result.stdout.find("Nodes in mesh:")
        if start_index != -1:
            # Extract the relevant section
            json_data = result.stdout[start_index:].split("Nodes in mesh:")[1].strip()
            json_data = json_data.split("\n\n")[0]  # Get only the first part if there are multiple sections
            
            # Load the JSON data into a Python dictionary
            nodes_info = json.loads(json_data)

            # Convert the nodes_info dictionary to a list of nodes
            parsed_nodes = []
            for node_id, node_data in nodes_info.items():
                parsed_nodes.append({
                    "id": node_id,  # Use the node ID as the key
                    "lastHeard": node_data.get("lastHeard", None),
                    "user": node_data.get("user", {}),
                    "deviceMetrics": node_data.get("deviceMetrics", {})
                })

            return {"nodes": parsed_nodes}  # Return the parsed nodes

        print("No nodes found in the output.")
        return None

    except subprocess.CalledProcessError as e:
        print(f"===>> Error running info command: {e}")
        print(f"===>> Command output (stdout): {e.stdout}")
        print(f"===>> Command output (stderr): {e.stderr}")

        # Attempt to parse any output that was captured
        if e.stdout:
            return parse_nodes_from_output(e.stdout)

    except json.JSONDecodeError as json_error:
        print(f"Error decoding JSON from stdout: {json_error}")

    except Exception as e:
        print(f"Unexpected error: {e}")

    return None  # Return None if no nodes were found or an error occurred

def parse_nodes_from_output(output):
    """Helper function to parse nodes from the command output."""
    nodes_info = {}
    start_index = output.find("Nodes in mesh:")
    if start_index != -1:
        json_data = output[start_index:].split("Nodes in mesh:")[1].strip()
        json_data = json_data.split("\n\n")[0]  # Get only the first part if there are multiple sections
        
        try:
            nodes_info = json.loads(json_data)
            # Convert the nodes_info dictionary to a list of nodes
            parsed_nodes = []
            for node_id, node_data in nodes_info.items():
                parsed_nodes.append({
                    "id": node_id,
                    "lastHeard": node_data.get("lastHeard", None),
                    "user": node_data.get("user", {}),
                    "deviceMetrics": node_data.get("deviceMetrics", {})
                })
            return {"nodes": parsed_nodes}  # Return the parsed nodes
        except json.JSONDecodeError as json_error:
            print(f"Error decoding JSON from captured output: {json_error}")
    
    return None  # Return None if no valid JSON data was found

'''# Example usage
if __name__ == "__main__":
    connection_string = "--host 192.168.1.100"  # Replace with actual connection string
    nodes_info = get_nodes_info(connection_string)
    if nodes_info:
        print("Nodes info retrieved successfully:")
        print(nodes_info)
    else:
        print("Failed to retrieve nodes info.")
'''