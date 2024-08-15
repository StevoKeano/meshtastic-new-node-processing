import subprocess
import serial.tools.list_ports
import sys
import json
import os
import re
import time
import threading
import shutil
from datetime import datetime, timedelta
import webbrowser
import urllib.parse
from pynput import keyboard
import meshtastic
import argparse
import platform
import asyncio
from bleak import BleakScanner
from bt_info import scan_bluetooth_devices, display_devices, get_user_selection, run_meshtastic_info

from pyfiglet import Figlet

from meshtastic.serial_interface import SerialInterface
from K3ANO_NewNodes.meshtastic_utils import find_meshtastic_port, get_nodes_info, load_existing_nodes, load_traceroute_log_nodes, issue_traceroute, save_node, sendMsg, update_welcome_message, load_settings
from colorama import init, Fore, Style
init()
############################################################################################################
# the magic sauce: https://www.perplexity.ai/search/why-does-past-here-throw-a-fil-q_Y1jRibQyy8mJfmMHjcsA  #
############################################################################################################
yourInviteString = "https://discord.gg/cpDFj345"  # Update this or you'll be sending MY NAME to everyone!'
welcomeMsg =  f"Welcome to the mesh! Join us on the AustinMesh discord chat: {yourInviteString}" # default value...
NODE_FILE =  os.path.join(os.path.dirname(__file__), 'nodes.txt')  # File to store node IDs
LOG_FILE = os.path.join(os.path.dirname(__file__), 'traceroute_log.txt')  # File to log traceroute output
sleepSeconds = 60  #set as needed...
port = ''   #'/dev/ttyACM0'  # I do a port check once per execution to Update this to your actual port
python_executable = "python"  # I also check what python you are at and update this
input_active = True
countdown_active = True

remaining_time = 0

# Global variables
current_window_title = ""

# Initialize flags for library availability
PYGETWINDOW_AVAILABLE = False
XLIB_AVAILABLE = False

# Try to import pygetwindow for Windows
if platform.system() == "Windows":
    try:
        import pygetwindow as gw
        PYGETWINDOW_AVAILABLE = True
    except ImportError:
        print("pygetwindow is not available.")

# Try to import Xlib for Linux
elif platform.system() == "Linux":
    try:
        from Xlib import X, display, Xatom, error
        import Xlib.protocol.event
        XLIB_AVAILABLE = True
    except ImportError:
        print("Xlib is not available.")

# Import win32gui for Windows
if platform.system() == "Windows":
    import win32gui


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
        
        # Use list form of command to avoid shell=True, which is more cross-platform friendly
        command = [python_executable, '-m', 'meshtastic', '--port', port, '--info']
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        
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

    # Convert the path to a URL
    clickable_path = urllib.parse.urljoin('file:', urllib.request.pathname2url(full_path))
    return clickable_path

# Flag to control the sleep thread
sleeping = True
def get_color_code(value, max_value):
    colors = [Fore.RED, Fore.YELLOW, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
    index = min(int(value / max_value * (len(colors) - 1)), len(colors) - 1)
    return colors[index]

def countdown_display(duration):
    global countdown_active
    start_time = time.time()
    max_remaining = duration  # Use the duration for max remaining time
    while countdown_active and time.time() - start_time < duration:
        remaining = int(duration - (time.time() - start_time))
        
        # Clear the line before printing the new message
        print(f"\r{' ' * 80}", end='', flush=True)  # Clear the line
        color = get_color_code(remaining, max_remaining)
        
        # Print the countdown message
        print(f"\r{Fore.YELLOW}{Style.BRIGHT}Press {Fore.GREEN}'L'{Fore.YELLOW} for TRACE log, {Fore.GREEN}'N'{Fore.YELLOW} for NODES, or {Fore.GREEN}'Q'{Fore.YELLOW} to quit.{Style.RESET_ALL} Continue in {color}{remaining:3d}{Style.RESET_ALL} seconds", end='', flush=True)
        
        time.sleep(0.1)


def get_active_window():
    system = platform.system()
    if system == "Windows":
        if PYGETWINDOW_AVAILABLE:
            return gw.getActiveWindow()
        else:
            print("pygetwindow is not available. Unable to get active window.")
            return None
    elif system == "Linux":
        if XLIB_AVAILABLE:
            d = display.Display()
            root = d.screen().root
            active_window = root.get_full_property(d.intern_atom('_NET_ACTIVE_WINDOW'), X.AnyPropertyType)
            if active_window:
                window = d.create_resource_object('window', active_window.value[0])
                return d, window
        return None
    else:
        print(f"Unsupported platform: {system}")
        return None

def set_window_name(display_window, new_name):
    system = platform.system()
    if system == "Windows":
        if PYGETWINDOW_AVAILABLE:
            try:
                hwnd = display_window._hWnd  # Get the window handle
                original_title = win32gui.GetWindowText(hwnd)
                print(f"Original window title: {original_title}")
                win32gui.SetWindowText(hwnd, new_name)
                time.sleep(1)  # Wait a bit to ensure the change takes effect
                updated_title = win32gui.GetWindowText(hwnd)
                print(f"Updated window title: {updated_title}")
                if updated_title == new_name:
                    print("Window title successfully updated.")
                else:
                    print("Window title did not update as expected.")
            except AttributeError:
                print("Error: Unable to set window title. The window object doesn't have a '_hWnd' attribute.")
            except Exception as e:
                print(f"Error setting window title: {str(e)}")
        else:
            print("pygetwindow is not available. Unable to set window name.")
    elif system == "Linux":
        print(f"display_window type: {type(display_window)}")
        print(f"display_window content: {display_window}")

        if isinstance(display_window, str):
            print("Warning: display_window is a string, which is not the expected format.")
            print("Attempting to set window name using xdotool...")
            try:
                # Use xdotool to set the window name
                subprocess.run(['xdotool', 'getactivewindow', 'set_window', '--name', new_name], check=True)
                print(f"Attempted to set window name to: {new_name}")
            except subprocess.CalledProcessError as e:
                print(f"Error using xdotool: {e}")
            except FileNotFoundError:
                print("xdotool is not installed. Please install it using 'sudo apt-get install xdotool'")
        elif XLIB_AVAILABLE:
            try:
                if isinstance(display_window, (list, tuple)) and len(display_window) == 2:
                    d, window = display_window
                elif hasattr(display_window, 'display') and hasattr(display_window, 'window'):
                    # Alternative structure where display_window is an object with display and window attributes
                    d, window = display_window.display, display_window.window
                else:
                    raise ValueError(f"Unsupported display_window structure: {display_window}")

                # Change the window property
                window.change_property(
                    d.intern_atom('_NET_WM_NAME'),
                    d.intern_atom('UTF8_STRING'),
                    8,
                    new_name.encode('utf-8')
                )
                d.flush()
                print(f"Attempted to set window name to: {new_name}")
            except Exception as e:
                print(f"Error setting window name: {str(e)}")
        else:
            print("Xlib is not available and display_window is not a string. Unable to set window name.")
    else:
        print(f"Unsupported platform: {system}")
    system = platform.system()
    if system == "Windows":
        if PYGETWINDOW_AVAILABLE:
            try:
                hwnd = display_window._hWnd  # Get the window handle
                original_title = win32gui.GetWindowText(hwnd)
                print(f"Original window title: {original_title}")
                win32gui.SetWindowText(hwnd, new_name)
                time.sleep(1)  # Wait a bit to ensure the change takes effect
                updated_title = win32gui.GetWindowText(hwnd)
                print(f"Updated window title: {updated_title}")
                if updated_title == new_name:
                    print("Window title successfully updated.")
                else:
                    print("Window title did not update as expected.")
            except AttributeError:
                print("Error: Unable to set window title. The window object doesn't have a '_hWnd' attribute.")
            except Exception as e:
                print(f"Error setting window title: {str(e)}")
        else:
            print("pygetwindow is not available. Unable to set window name.")
    elif system == "Linux":
        if XLIB_AVAILABLE:
            try:
                d, window = display_window
                window.change_property(
                    d.intern_atom('_NET_WM_NAME'),
                    d.intern_atom('UTF8_STRING'),
                    8,
                    new_name.encode('utf-8')
                )
                d.flush()
                print("Window title change attempted. Please check if it was successful.")
            except Exception as e:
                print(f"Error setting window name: {str(e)}")
        else:
            print("Xlib is not available. Unable to set window name.")
    else:
        print(f"Unsupported platform: {system}")

def update_window_title():
    global current_window_title, input_active
    while input_active:
        current_window_title = get_active_window()
        time.sleep(0.5)

def get_window_title(window):
    if window is None:
        return ""
    system = platform.system()
    if system == "Windows":
        return window.title
    elif system == "Linux":
        d, w = window
        return w.get_wm_name()
    return ""

def get_clickable_path(file_name):
    # Get the current working directory
    cwd = os.getcwd()
    full_path = os.path.join(cwd, file_name)

    # Convert the path to a URL
    clickable_path = urllib.parse.urljoin('file:', urllib.request.pathname2url(full_path))
    return clickable_path

def handle_user_input(duration):
    global input_active, countdown_active
    input_active = True
    countdown_active = True
  #  print(f"Entered handle_user_input with duration: {duration}")

    def on_press(key):
        global input_active, countdown_active
        # print(f"Key pressed: {key}")
        try:
            active_window = get_active_window()
            window_title = get_window_title(active_window)
 #           print(f"Current window title: {window_title}")

            if hasattr(key, 'char') and key.char is not None:
                if 'K3ANO' in window_title:
                    if key.char.lower() == 'l':
                        webbrowser.open(get_clickable_path(LOG_FILE))
                        print("\rOpening TRACE log file...", end='', flush=True)
                    elif key.char.lower() == 'n':
                        webbrowser.open(get_clickable_path(NODE_FILE))
                        print("\rOpening NODES log file...", end='', flush=True)
                    elif key.char.lower() == 'q':
                        print("\rExiting user input handling.", end='', flush=True)
                        input_active = False
                        countdown_active = False
                        return False  # Stop listener
#                else:
 #                   print("Not in K3ANO window, ignoring key press")
  #          else:
   #             print("Special key pressed, ignoring...")
        except Exception as e:
            print(f"Error handling key press: {e}")

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    # note to reviewer "Keyboard listener started so you can open log files while in newNodes window"

    start_time = time.time()
    while input_active and countdown_active:
        current_time = time.time()
        elapsed_time = current_time - start_time
        remaining_time = max(0, duration - elapsed_time)
        
       # print(f"Elapsed time: {elapsed_time:.2f}s, Remaining time: {remaining_time:.2f}s")

        if remaining_time == 0:
          #  print("Countdown reached zero, exiting loop")
            break  # Exit the loop when the countdown reaches zero

        time.sleep(0.1)

    # Ensure countdown_active is set to False when exiting
    countdown_active = False
    listener.stop()


# Start the window title update thread
# threading.Thread(target=update_window_title, daemon=True).start()

# Function to sleep for a specified duration and then allow user input
def sleep_and_prompt(sleep_duration):
    global sleeping
    while True:
        time.sleep(sleep_duration)
        if sleeping:
            print(f"\nSleep time of {sleep_duration} seconds is up.")


async def main():
    global port, welcomeMsg, NODE_FILE, LOG_FILE, input_active, countdown_active, sleepSeconds

    # Start the window title update thread so we know what window dork is on...
    threading.Thread(target=update_window_title, daemon=True).start()

    port, verbose, useSettingsMsg = parse_arguments()
    print(f"Port: {port}")
    print(f"Verbose: {verbose}")

    sleep_seconds = sleepSeconds

    new_name = "K3ANO: newNodes Welcome to AustinMESH"
    active_window = get_active_window()
    if active_window:
        set_window_name(active_window, new_name)
        print(f"Attempted to set window name to: {new_name}")
    else:
        print("Could not get active window")

    f = Figlet(font='slant')
     # Render text
    text_k3ano = f.renderText('K 3 A N O')
    text_austinmesh = f.renderText('AUSTINMESH')
    text_org = f.renderText(' . o r g  ')

    # Print text in dark maroon (approximated with red)
    print(Fore.RED + Style.DIM + text_k3ano)

    # Print text in dark orange (approximated with yellow)
    print(Fore.YELLOW + Style.DIM + text_austinmesh)
    print(Fore.YELLOW + Style.DIM + text_org)

    if not useSettingsMsg:
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

    if not port:
        connection_type = input("Is the Meshtastic device connected via USB (C), IP (I), BT (B)? ").strip().lower()

        if connection_type == 'c':
            port = find_meshtastic_port()  # Ensure this function is cross-platform
        elif connection_type == 'i':
            ip_address = input("Enter the IP address of the Meshtastic device: ")
            port = f"--host {ip_address}"
        elif connection_type == 'b':
            #port = f"--host {ip_address}"
                devices = await scan_bluetooth_devices()
                display_devices(devices)
    
                if not devices:
                    return  # Exit if no devices found
    
                selected_device = get_user_selection(devices)
                print(f"Selected device: Address: {selected_device.address}, Name: {selected_device.name or 'Unknown'}")

                # Check if the device is already paired
                input("Please ensure the device is paired on your computer. Press Enter to continue...")
                time.sleep(2)  # Pause briefly to allow pairing process to complete

                # Attempt to run the Meshtastic command directly
                success = run_meshtastic_info(selected_device.address)
                port = f"--ble {selected_device.address}"
        else:
            print("Invalid input. Please enter 'C' for USB,  'I' for IP, 'B' for Bluetooth.")
            return None

        if port is None:
            print("No Meshtastic device found. Please check the connection.")
            return None

    print(f"Meshtastic device found?: {port}")

    connection_string = f'--host {port[7:]}' if port.startswith('--host') else f'{port}' if port.startswith('--ble') else f'--port {port}'
    print(f"connection_string = {connection_string}")
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
                  
                    print(f"{Fore.GREEN}Node {node_id} last heard {time_since_last_heard.total_seconds() / 3600:.2f} hours ago")
                    if time_since_last_heard <= timedelta(hours=2):
                        if node_id in traceroute_log_nodes:
                            print(f"{Fore.YELLOW}Skipping node {node_id} as it's already in the traceroute log.")
                        elif node_id not in existing_nodes:
                            print(f"New node detected: {node_id}")
                            traceroute_successful = issue_traceroute(node_id, connection_string)
                            if traceroute_successful:
                                save_node(node_id, last_heard, user, deviceMetrics, current_time.strftime("%Y-%m-%d %H:%M:%S"))
                                sendMsg(node_id, welcome_message, connection_string)
                            else:
                                save_node(node_id, last_heard, user, deviceMetrics, current_time.strftime("%Y-%m-%d %H:%M:%S"))
                                sendMsg(node_id, welcome_message, connection_string)
                    else:
                        print(f"{Fore.WHITE}{Style.BRIGHT} Skipping node {node_id} as it hasn't been heard from in over 2 hours.")
                else:
                    print(f"{Fore.YELLOW}{Style.BRIGHT}No last heard time available for node {node_id}")

        else:
            print("Failed to retrieve nodes info. Retrying in next iteration.")

        print(f"{Fore.CYAN}{Style.BRIGHT}\033[4mNode file: {get_clickable_path(NODE_FILE)}\033[0m")
        print(f"{Fore.CYAN}{Style.BRIGHT}\033[4mTrace Log file: {get_clickable_path(LOG_FILE)}\033[0m")


        input_active = True
        countdown_active = True
        # print('call countdown_display as target of a thread...')
        display_thread = threading.Thread(target=countdown_display, args=(sleep_seconds,), daemon=True)
        display_thread.start()

        handle_user_input(sleep_seconds)

        countdown_active = False
        display_thread.join()

        print(f"\nSleep time of {sleep_seconds} seconds is up. Continuing with the program.")

if __name__ == "__main__":
    asyncio.run(main())