Send a welcome message and run traceroute on new meshtastic nodes before they disappear! (traceroute requires USB connected meshtastic radio).
see log files after execution.  SEE SETUP FOR PYTHON, PIP AND MESHTASTIC install...

download the lot and run below command.  

======================== o u t p u t ====================================

D:\dev\python\mesh>python newNode.py

Is the Meshtastic device connected via USB (C) or IP (I)? c
Scanning for Meshtastic device...

Checking port: COM4
Meshtastic device found on COM4
Meshtastic device found: COM4
Current time: 2024-07-29 17:10:25
Node !06e2718a last heard -0.00 hours ago
New node detected: !06e2718a
Sending traceroute request to !06e2718a (this could take a while)
Error running traceroute for !06e2718a: 2024-07-29 17:11:30 - !06e2718a
Node !1c314db4 last heard 10.50 hours ago
Skipping node !1c314db4 as it hasn't been heard from in over 2 hours.
Node !53d56b71 last heard 0.07 hours ago
New node detected: !53d56b71
Sending traceroute request to !53d56b71 (this could take a while)
2024-07-29 17:11:33 - Traceroute output for !53d56b71: !06e2718a --> !53d56b71
Connected to radio
Sending text message Welcome to the mesh! Join us on the AustinMesh discord chat: https://discord.gg/cpDFj345 to !53d56b71 on channelIndex:0

Node !1c498944 last heard 0.08 hours ago
New node detected: !1c498944
Sending traceroute request to !1c498944 (this could take a while)
2024-07-29 17:11:40 - Traceroute output for !1c498944: !06e2718a --> !1c49894

4
Connected to radio
Sending text message Welcome to the mesh! Join us on the AustinMesh discord chat: https://discord.gg/cpDFj345 to !1c498944 on channelIndex:0

Sleeping for 180 seconds from 2024-07-29 17:10:25
