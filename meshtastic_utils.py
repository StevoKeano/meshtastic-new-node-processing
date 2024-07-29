'''
Meshtastic CLI and Python library work on Linux as well. The core functionality is cross-platform and supports Windows, macOS, and Linux. 

Here are a few key points about using Meshtastic on Linux:

Installation: You can install the Meshtastic Python package on Linux using pip:

pip install meshtastic

Serial port access: On Linux, serial ports are typically named like /dev/ttyUSB0 or /dev/ttyACM0.
You may need to add your user to the dialout group to access these ports without sudo:

sudo usermod -a -G dialout $USER

Command usage: The CLI commands work the same way on Linux as they do on other platforms. For example:

meshtastic --port /dev/ttyUSB0 --info
'''



import subprocess
import serial.tools.list_ports
import sys

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

if __name__ == "__main__":
    port = find_meshtastic_port()
    if port:
        print(f"The active Meshtastic port is: {port}")
    else:
        print("No Meshtastic device found")