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
from meshtastic_utils import find_meshtastic_port


# Configuration
yourInviteString = "https://discord.gg/cpDFj345"  # Update this or you'll be sending MY NAME to everyone!'
welcomeMsg = "Welcome to the mesh! Join us on the AustinMesh discord chat:"

sleepSeconds = 181  #set as needed...
port = '/dev/ttyACM0'  # I do a port check once per execution to Update this to your actual port
python_executable = "python"  # I also check what python you are at and update this

NODE_FILE = 'nodes.txt'  # File to store node IDs
LOG_FILE = 'traceroute_log.txt'  # File to log traceroute output

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


def sendMsg(msg: str) -> None:
    """
    Send a message via Meshtastic.

    Args:
    msg (str): The message to send.

    Returns:
    None
    """
    try:
        # Connect to the Meshtastic device
        interface = SerialInterface()

        # Send the text message
        interface.sendText(msg)

        print(f"Message sent: {msg}")

    except Exception as e:
        print(f"Error sending message: {e}")

    finally:
        # Close the interface
        if 'interface' in locals():
            interface.close()



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

def save_node(node_id):
    """Save a new node ID to the node file."""
    with open(NODE_FILE, 'a') as f:
        f.write(f"{node_id}\r")  # CRLF at end of line

def issue_traceroute(node_id):
    """Run traceroute on the new node and log the output."""
    global python_executable
    try:
        command = [sys.executable, '-m', 'meshtastic', '--traceroute', node_id]
        print(f'Sending traceroute request to {node_id}  (this could take a while)')
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(result.stdout)

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
                log_file.write(f"{log_entry}\r")  # \r\n  Log the entry with timestamp
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
            log_file.write(f"{error_message}\r")  # \r\n Log the error message with timestamp
        return False  # Indicate failure



def main():
          """Main function to fetch nodes, check for new ones, and run traceroute."""
          global port  # Declare that we are using the global variable
          port = find_meshtastic_port()
    
          if port is None:
             print("No Meshtastic device found. Please check the connection.")
             return None

          print(f"Meshtastic device found on port: {port}")
            
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
                        sendMsg(f"{welcomeMsg}{yourInviteString}")
            print(f'sleep {sleepSeconds} seconds from ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')  )
            # Sleep for 3 minutes (180 seconds)
            time.sleep(sleepSeconds)
    
if __name__ == "__main__":
    main()

