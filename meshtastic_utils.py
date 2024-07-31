import subprocess
import serial.tools.list_ports
import sys
import json
import os  

from datetime import datetime, timedelta

timeoutSeconds = 10
NODE_FILE = 'nodes.txt'  # File to store node IDs
LOG_FILE = 'traceroute_log.txt'  # File to log traceroute output
yourInviteString = "https://discord.gg/cpDFj345"  # Update this or you'll be sending MY NAME to everyone!'
welcomeMsg =  f"Welcome to the mesh! Join us on the AustinMesh discord chat: {yourInviteString}" # default value...

def load_settings():
    global welcomeMsg
    try:
        with open('settings.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {"welcome_message": welcomeMsg}

def update_welcome_message(change="y"):
    global welcomeMsg
    settings = load_settings()
    current_message = settings.get('welcome_message',  welcomeMsg)
    
 #   print(f"Current welcome message: {current_message}")
  #  change = input("Do you want to change the welcome message? (y/n): ").strip().lower()
    
    if change == 'y':
        new_message = input("Enter the new welcome message: ")
        settings['welcome_message'] = new_message
        
        with open('settings.json', 'w') as file:
            json.dump(settings, file, indent=2)        
        print("Welcome message updated successfully!")
        return(new_message)
    else:
        print("Welcome message remains unchanged.")


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
    command = f'{sys.executable} -m meshtastic --host {ip_address} --info'
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, timeout=timeoutSeconds)
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
    command = f'{sys.executable} -m meshtastic {connection_string} --sendtext "{message}" --dest {node_id}'
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error sending message to {node_id}: {e}")
        print(f"Command output: {e.stderr}")

#def load_existing_nodes():
 #   """Load existing node IDs from the node file."""
  #  if os.path.exists(NODE_FILE):
   #     with open(NODE_FILE, 'r') as f:
    #        return {line.strip() for line in f if line.strip()}
    #return set()

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

#def save_node(node_id):
 #   """Save a new node ID to the node file."""
  #  with open(NODE_FILE, 'a') as f:
   #     f.write(f"{node_id}\r")  # CRLF at end of line

def save_node(node_id, last_heard=None, user=None, device_metrics=None, seenTime=None):
    """Save a new node ID along with lastHeard, user, and deviceMetrics to the node file."""
    # Prepare the output line with the provided data
    output_line = f"{node_id},{last_heard},{user},{device_metrics},{seenTime}\r"  # CRLF at end of line
    with open(NODE_FILE, 'a') as f:
        f.write(output_line)

def issue_traceroute(node_id, connection_string):
    """Run traceroute on the new node and log the output."""
    global python_executable
    try:
        # Prepare the command with the connection string
        if connection_string.startswith('--host'):
            parts = connection_string.split()
            protocol = parts[0]
            ip = parts[1]
            command = [sys.executable, '-m', 'meshtastic', protocol, ip,   '--traceroute', node_id]  # remote IP
        else:
            command = [sys.executable, '-m', 'meshtastic',  '--traceroute', node_id] # USB Port

        print(f'Sending traceroute request to {node_id} (this could take a while)')
        
        # Run the traceroute command
        #print(f"run this ?? ...   {command}")
        try:
            result = None
            result = subprocess.run(command, check=True, capture_output=True, text=True, shell=True)

        except subprocess.CalledProcessError as e:
            print("An error occurred while running the command:")
            print("Return code:", e.returncode)
            print("Output:", e.output)
            print("Error message:", e.stderr)

        except FileNotFoundError:
            print("The specified Python executable was not found. Please check the path.")

        except Exception as e:
            print("An unexpected error occurred:", str(e))
           # print(result.stdout)

        # Extract the relevant traceroute line
        traceroute_line = None
        if result != None:
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
                log_file.write(f"No valid traceroute output for {node_id}.\n")  # Log the entry with timestamp
            return False  # Indicate failure

    except subprocess.CalledProcessError as e:
        # Log the error message in the specified format with timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get the current date and time
        error_message = f"{timestamp} - {node_id} {e.stderr.strip()}"
        print(f"Error running traceroute for {node_id}: {error_message}")  # Print the error output
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f"{error_message}\n")  # Log the error message with timestamp
        return False  # Indicate failure

def find_meshtastic_port():
    ports = sorted(serial.tools.list_ports.comports(), key=lambda x: x.device, reverse=True)
    
    print("Scanning for Meshtastic device...")
    for port in ports:
        print(f"\nChecking port: {port.device}")
        if check_meshtastic_port(port.device):
            return port.device

    print("No Meshtastic device found on COM ports.")
    
    # If no COM ports were found, ask for IP address
    ip_address = input("Enter IP address of the Meshtastic device (or press Enter to exit): ")
    
    if ip_address:
        if check_meshtastic_ip(ip_address):
            return f"--host {ip_address}"
    
    return None

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
    command = f'{sys.executable} -m meshtastic --host {ip_address} --info'
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, timeout=timeoutSeconds)
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



def get_nodes_info(connection_string):
    """Get the list of nodes and their info using Meshtastic CLI."""
    command = f'{sys.executable} -m meshtastic {connection_string} --info'
    nodes_info = []  # Initialize nodes_info at the start

    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, timeout=10)
        
        # Print raw output for debugging
        #print("Raw output from --info command:")
        #print(result.stdout)

        # Attempt to parse the output as JSON
        start_index = result.stdout.find("Nodes in mesh:")
        if start_index != -1:
            # Extract the relevant section
            json_data = result.stdout[start_index:].split("Nodes in mesh:")[1].strip()
            json_data = json_data.split("\n\n")[0]  # Get only the first part if there are multiple sections
            
            # Debug print for extracted JSON data
            #print("Extracted JSON data:")
           # print(json_data)

            # Load the JSON data into a Python dictionary
            nodes_info = json.loads(json_data)

            # Convert the nodes_info dictionary to a list of nodes
            parsed_nodes = []
            for node_id, node_data in nodes_info.items():
                # Debug print for each node being processed
             #   print(f"Processing node ID: {node_id}, Data: {node_data}")
                
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
            try:
                start_index = e.stdout.find("Nodes in mesh:")
                if start_index != -1:
                    json_data = e.stdout[start_index:].split("Nodes in mesh:")[1].strip()
                    json_data = json_data.split("\n\n")[0]  # Get only the first part if there are multiple sections
                    #print("Extracted JSON data from error output:")
                    #print(json_data)

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
                print(f"Error decoding JSON from stdout: {json_error}")

    except Exception as e:
        print(f"Unexpected error: {e}")

    return None  # Return None if no nodes were found or an error occurred