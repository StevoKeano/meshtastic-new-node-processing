#!/usr/bin/env python3

import subprocess
import os

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the full path to newNode.py
newnode_path = os.path.join(script_dir, 'newNode.py')

# Start newNode.py as a background process
subprocess.Popen(['python3', newnode_path], 
                 stdout=subprocess.DEVNULL, 
                 stderr=subprocess.DEVNULL, 
                 start_new_session=True)

print("newNode.py has been started in the background.")

