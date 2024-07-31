import keyboard
import sys
import platform
import serial
import serial.tools.list_ports
import shutil  # Add this import
import time
import threading
from datetime import datetime, timedelta
import subprocess
import os
import re
import meshtastic
import webbrowser
import pygetwindow as gw
import argparse

from meshtastic.serial_interface import SerialInterface
from K3ANO_NewNodes.meshtastic_utils import find_meshtastic_port, get_nodes_info, load_existing_nodes, load_traceroute_log_nodes, issue_traceroute, save_node, sendMsg, update_welcome_message, load_settings
#from K3ANO_NewNodes.meshtastic_utils import find_meshtastic_port, get_nodes_info, load_existing_nodes, load_traceroute_log_nodes, issue_traceroute, save_node, sendMsg, update_welcome_message, load_settings
# Configuration
yourInviteString = "https://discord.gg/cpDFj345"  # Update this or you'll be sending MY NAME to everyone!'
welcomeMsg =  f"Welcome to the mesh! Join us on the AustinMesh discord chat: {yourInviteString}" # default value...
NODE_FILE = 'nodes.txt'  # File to store node IDs
LOG_FILE = 'traceroute_log.txt'  # File to log traceroute output
sleepSeconds = 60  #set as needed...
port = ''   #'/dev/ttyACM0'  # I do a port check once per execution to Update this to your actual port
python_executable = "python"  # I also check what python you are at and update this
input_active = True
countdown_active = True

remaining_time = 0

def parse_arguments():
    parser = argparse.ArgumentParser(description="Radio connection setup")
    
    # Add arguments
    parser.add_argument("--p", nargs=2, metavar=("type", "value"), help="Port connection type and value. Ex --p c COM9 OR --p c /dev/ttyACM0 or --p i 192.168.1.87")
    parser.add_argument("--m", action="store_true", help="Use message from settings.json file")
    parser.add_argument("--v", action="store_true", help="Enable verbose debug mode")

    # Parse arguments
    args = parser.parse_args()

    # Initialize variables
    port = None
    verbose = False
    useSettingsMsg = False

    # Process arguments
    if args.p:
        connection_type, connection_value = args.p
        if connection_type == "i":
            port = f"--host {connection_value}"
        elif connection_type == "c":
            port = connection_value
        else:
            print(f"Invalid connection type: {connection_type}")
            sys.exit(1)

    if args.m:
        useSettingsMsg = True

    if args.v:
        verbose = True

    return port, verbose, useSettingsMsg


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

# Function to create clickable file paths
def get_clickable_path(file_name):
    # Get the current working directory
    cwd = os.getcwd()
    full_path = os.path.join(cwd, file_name)

    # Use forward slashes for the URL
    clickable_path = full_path.replace("\\", "/")  # Replace backslashes with forward slashes
    return f'file:///{clickable_path}'  # Create the clickable file URL

# Flag to control the sleep thread
sleeping = True

def countdown_display(duration):
    global countdown_active
    start_time = time.time()
    while countdown_active and time.time() - start_time < duration:
        remaining = int(duration - (time.time() - start_time))
        print(f"\rPress 'L' for TRACE log, 'N' for NODES, or 'Q' to quit. Continue in {remaining:3d} seconds", end='', flush=True)
        time.sleep(0.1)

def handle_user_input(duration):
    global input_active, countdown_active
    
    start_time = time.time()
    while input_active and countdown_active:
        current_time = time.time()
        elapsed_time = current_time - start_time
        remaining_time = max(0, duration - elapsed_time)
        
        if remaining_time == 0:
            break  # Exit the loop when the countdown reaches zero

        active_window = gw.getActiveWindow()
        if active_window and 'nodes' in active_window.title.lower():
            if keyboard.is_pressed('l'):
                webbrowser.open(get_clickable_path(LOG_FILE))
                for i in range(1, 16):
                    print("\rOpening TRACE log file...", end='', flush=True)
                    time.sleep(0.05)
            elif keyboard.is_pressed('n'):
                webbrowser.open(get_clickable_path(NODE_FILE))
                for i in range(1, 16):
                    print("\rOpening NODES log file...", end='', flush=True)
                    time.sleep(0.05)
            elif keyboard.is_pressed('q'):
                for i in range(1, 16):
                    print("\rExiting user input handling.", end='', flush=True)
                    time.sleep(0.01)
                input_active = False
                countdown_active = False
                break
        time.sleep(0.1)

    # Ensure countdown_active is set to False when exiting
    countdown_active = False


# Function to sleep for a specified duration and then allow user input
def sleep_and_prompt(sleep_duration):
    global sleeping
    while True:
        time.sleep(sleep_duration)
        if sleeping:
            print(f"\nSleep time of {sleep_duration} seconds is up. You can continue using the program.")

def main():
    global port,welcomeMsg, NODE_FILE, LOG_FILE, input_active, countdown_active

    port, verbose, useSettingsMsg = parse_arguments()
    # Print results
    print(f"Port: {port}")
    print(f"Verbose: {verbose}")

    sleep_seconds = sleepSeconds

    if useSettingsMsg==False:
        # manage welcome message
        settings = load_settings()
        welcome_message = settings.get('welcome_message', welcomeMsg)
        print(f"Using:  {welcome_message}")
        change = input("Do you want to change the above welcome message? (y/n): ").strip().lower()
        update_welcome_message(change)
        settings = load_settings()
        welcome_message = settings.get('welcome_message', welcomeMsg)
    else:
        settings = load_settings()
        welcome_message = settings.get('welcome_message', welcomeMsg)
        print(f"Using:  {welcome_message}")

    """Main function to fetch nodes, check for new ones, and run traceroute."""
    if port == '':
        # Ask the user for the connection type ?
        connection_type = input("Is the Meshtastic device connected via USB (C) or IP (I)? ").strip().lower()
    #    connection_type = input("Is the Meshtastic device connected via USB (C) or IP (I) or IP --traceroute (ITR)? ").strip().lower()

        if connection_type == 'c':
            port = find_meshtastic_port()  # This will find the COM port
        elif connection_type == 'i':
            ip_address = input("Enter the IP address of the Meshtastic device: ")
            port = f"--host {ip_address}"  # Set the port to the IP address
        elif connection_type == 'itr':
            ip_address = input("Enter the IP address of the Meshtastic device: ")
            port = f"--host {ip_address}"  # Set the port to the IP address
        else:
            print("Invalid input. Please enter 'C' for USB or 'I' for IP.")
            return None

        if port is None:
            print("No Meshtastic device found. Please check the connection.")
            return None

    print(f"Meshtastic device found?: {port}")

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
        print(f"Current welcome message: {welcome_message}")
        input_active = True
        remaining_time = sleep_seconds
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
                            # Run traceroute and check success  
                            traceroute_successful = issue_traceroute(node_id,connection_string)
                            if traceroute_successful:
                                save_node(node_id, last_heard, user, deviceMetrics,current_time.strftime("%Y-%m-%d %H:%M:%S"))  # Only save the node if traceroute was successful
                                sendMsg(node_id,welcome_message,connection_string)
                            else:
                                save_node(node_id, last_heard, user, deviceMetrics,current_time.strftime("%Y-%m-%d %H:%M:%S"))  # Only save the node if traceroute was successful
                                sendMsg(node_id,welcome_message,connection_string)
                    else:
                        print(f"Skipping node {node_id} as it hasn't been heard from in over 2 hours.")
                else:
                    print(f"No last heard time available for node {node_id}")

        else:
            print("Failed to retrieve nodes info. Retrying in next iteration.")

        # Print clickable paths
        print(f"Node file: {get_clickable_path(NODE_FILE)}")
        print(f"Trace Log file: {get_clickable_path(LOG_FILE)}")
#        webbrowser.open(get_clickable_path(LOG_FILE))
        #print(f'Sleeping for 180 seconds from {current_time.strftime("%Y-%m-%d %H:%M:%S")}')
        #time.sleep(sleepSeconds)
        #sleep_seconds = sleepSeconds  # Set your desired sleep duration
         # Reset for the next iteration
        input_active = True
        countdown_active = True

        # Start the countdown display in a separate thread
        display_thread = threading.Thread(target=countdown_display, args=(sleep_seconds,), daemon=True)
        display_thread.start()

        # Handle user input in the main thread
        handle_user_input(sleep_seconds)

        # Ensure the countdown display stops
        countdown_active = False
        display_thread.join()


        print(f"\nSleep time of {sleep_seconds} seconds is up. Continuing with the program.")

 
 

if __name__ == "__main__":
    main()