# UVA Occultation Script Generation with Python
This is a Python conversion of the awk code to generate sequence scripts for Sharpcap

# GUI Interface
## How to run
python script_generation_GUI.py

This works with command prompt and linux terminals. You will need script_generation_GUI.py and script_generation_func.py in the same folder. 

## Navigation
Upload raw events.txt file by clicking on the Upload events.txt button in the top left corner. This file **must** be named according to YYYYMMDD_events.txt as it infers the day from the file name. The file is created from the events page of Occult4

If pre and post files are in different locations, use the browse buttons to set their locations. If you want the script to save in a different location, you can set that via the respective browse button as well. By default, the script will save in the same folder as the python files.

Change the telescope type using the radio buttons to change the restrictions applied on the events.

Click on an event and click Move to Accepted/Rejected to move them around. Events in green are prob > 15% and yellow are events that are within 4 minutes of each other. 
Clicking on an event will autoselect the next one. Use the arrow keys to move the selection up and down, and press space to move them to either rejected or accepted. Pressing enter will move the selection down.

Finally click on Generate SCS from Accepted in the bottom right corner to create a script. 

## Configuration
To change the mag and duration conditions or the telescope names, edit the telescope_accept_mask in script_generation_func.py. As of 20260215, it can handle 3 types of telescopes. If changing telescope names, you will also need to edit the list next to the comment #CHANGE AS TELESCOPES ARE ADDED in script_generation_GUI.py

To change the background colors of the close/good events, edit the color hex code in _configure_row_tags in script_generation_GUI.py

# CLI Interface (OLD)
## How to run
python script_generation_CLI.py [event file] [telescope] [**--day** day of observation] [**--pre** header file] [**--post** footer file] [**--out** output path]

This works with command prompt and linux terminals.

## Options
**event file**

This is the YYYYMMDD_events.txt file which contains the raw events list. If in another folder, enter the path to it .../YYYYMMDD_events.txt

**telescope**

This is the telescope system you are generating the script for. Current options are: c11, c14, hubble24 

**day**

Optional. Day of observation of the event list. If not entered, program will infer the day from the events.txt file name

**pre**

Optional. This is the header file that contains the setup instructions. Default is pre174.txt. If in another folder, enter the path to it .../pre174.txt

**post**

Optional. This is the footer file that contains the end of observing sequence. Default is post571.txt. If in another folder, enter the path to it .../post571.txt

**out**

Optional. Can use -o or --out. This sets the path for the output scs file. Default will save as YYYYMMDD_174_script.scs and will save in the same location as the program. To set a different path, enter .../YYYYMMDD_174_script.scs

# Notes
- Need to handle UTC date change errors from SharpCap




