import sys
import platform
import serial
import serial.tools.list_ports
import shutil  # Add this import
import time
from datetime import datetime, timedelta
import subprocess
import os
import re
import meshtastic

from meshtastic.serial_interface import SerialInterface
from meshtastic_utils import find_meshtastic_port, get_nodes_info, load_existing_nodes, load_traceroute_log_nodes, issue_traceroute, save_node, sendMsg



# Configuration
yourInviteString = "https://discord.gg/cpDFj345"  # Update this or you'll be sending MY NAME to everyone!'
welcomeMsg = "Welcome to the mesh! Join us on the AustinMesh discord chat:"

sleepSeconds = 181  #set as needed...
port = '/dev/ttyACM0'  # I do a port check once per execution to Update this to your actual port
python_executable = "python"  # I also check what python you are at and update this


import sys
import subprocess

def get_python_command():
    # Get the version info
    version_info = sys.version_info

    # Check if we're running under Python 2 or Python 3
    if version_info.major == 3:
        python_command = 'python3'
    else:
        python_command = 'python'

    # Verify the command exists
    if shutil.which(python_command) is None:
        # If the default doesn't exist, try the alternative
        alternative = 'python' if python_command == 'python3' else 'python3'
        if shutil.which(alternative) is not None:
            python_command = alternative
        else:
            print("Unable to determine Python command. Defaulting to 'python'")
            python_command = 'python'

    return python_command

def get_nodes():
    """Fetch the current node list from the Meshtastic device."""
    try:
        global python_executable
           # Store the result in a variable
        python_executable = get_python_command()
      
        
        command = f'{python_executable} -m meshtastic --port {port} --info'
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

def main():
    """Main function to fetch nodes, check for new ones, and run traceroute."""
    global port  # Declare that we are using the global variable

        # Ask the user for the connection type
    connection_type = input("Is the Meshtastic device connected via USB (C) or IP (I)? ").strip().lower()

    if connection_type == 'c':
        port = find_meshtastic_port()  # This will find the COM port
    elif connection_type == 'i':
        ip_address = input("Enter the IP address of the Meshtastic device: ")
        port = f"--host {ip_address}"  # Set the port to the IP address
    else:
        print("Invalid input. Please enter 'C' for USB or 'I' for IP.")
        return None

    if port is None:
        print("No Meshtastic device found. Please check the connection.")
        return None

    print(f"Meshtastic device found: {port}")

    # If port starts with '--host', it's an IP address
    if port.startswith('--host'):
        # Use the entire string (including --host) when running commands
        connection_string = port
    else:
        # For COM ports, use --port
        connection_string = f'--port {port}'

    while True: 
        current_time = datetime.now()
        print(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

        nodes_info = get_nodes_info(connection_string)
        
        if nodes_info is not None:
            existing_nodes = load_existing_nodes()
            traceroute_log_nodes = load_traceroute_log_nodes()

            for node in nodes_info.get("nodes", []):
                node_id = node.get("id")
                last_heard = node.get("lastHeard")
                user = node.get("user")
                deviceMetrics = node.get("deviceMetrics")
                
                if last_heard:
                    last_heard_time = datetime.fromtimestamp(last_heard)
                    time_since_last_heard = current_time - last_heard_time
                    
                    print(f"Node {node_id} last heard {time_since_last_heard.total_seconds() / 3600:.2f} hours ago")

                    if time_since_last_heard <= timedelta(hours=2):
                        if node_id in traceroute_log_nodes:
                            print(f"Skipping node {node_id} as it's already in the traceroute log.")
                        elif node_id not in existing_nodes:
                            print(f"New node detected: {node_id}")
                            if port.startswith('--host'):                            
                                    save_node(node_id, last_heard, user, deviceMetrics,current_time.strftime("%Y-%m-%d %H:%M:%S"))  # Only save the node if remote IP device
                                    sendMsg(node_id, f"Welcome to the mesh! Join us on the AustinMesh discord chat: {yourInviteString}",connection_string)
                            else:
                                # Run traceroute and check success  
                                traceroute_successful = issue_traceroute(node_id,connection_string)
                                if traceroute_successful:
                                   save_node(node_id, last_heard, user, deviceMetrics,current_time.strftime("%Y-%m-%d %H:%M:%S"))  # Only save the node if traceroute was successful
                                   sendMsg(node_id, f"Welcome to the mesh! Join us on the AustinMesh discord chat: {yourInviteString}",connection_string)
                    else:
                        print(f"Skipping node {node_id} as it hasn't been heard from in over 2 hours.")
                else:
                    print(f"No last heard time available for node {node_id}")

        else:
            print("Failed to retrieve nodes info. Retrying in next iteration.")

        print(f'Sleeping for 180 seconds from {current_time.strftime("%Y-%m-%d %H:%M:%S")}')
        time.sleep(sleepSeconds)

if __name__ == "__main__":
    main()
