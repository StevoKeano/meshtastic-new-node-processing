import subprocess
import serial.tools.list_ports
import sys
import json
from datetime import datetime, timedelta

def find_meshtastic_port():
    ports = sorted(serial.tools.list_ports.comports(), key=lambda x: x.device, reverse=True)
    
    print("Scanning for Meshtastic device...")
    for port in ports:
        print(f"\nChecking port: {port.device}")
        print(f"  Description: {port.description}")
        print(f"  Manufacturer: {port.manufacturer}")
        print(f"  Hardware ID: {port.hwid}")
        print(f"  VID:PID: {port.vid:04X}:{port.pid:04X}")
        print(f"  Serial Number: {port.serial_number}")
        print(f"  Location: {port.location}")
        print(f"  Product: {port.product}")
        print(f"  Interface: {port.interface}")
        
        if check_meshtastic_port(port.device):
            return port.device

    print("No Meshtastic device found after checking all ports.")
    return None

def check_meshtastic_port(port):
    command = f'{sys.executable} -m meshtastic --port {port} --info'
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, timeout=5)
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

def get_nodes_info():
    """Get the list of nodes and their info using Meshtastic CLI."""
    global port
    command = [sys.executable, '-m', 'meshtastic', '--port', port, '--info']
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running info command: {e}")
        print(f"Command output: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON output: {e}")
        return None