# UVA Occultation Script Generation with Python
This is a Python conversion of the awk code to generate sequence scripts for Sharpcap

## How to run
python script_generation.py [event file] [**--day** day of observation] [**--pre** header file] [**--post** footer file] [**--out** output path]

This works with command prompt and linux terminals.

## Options
**event file**

This is the YYYYMMDD_events.txt file which contains the raw events list. If in another folder, enter the path to it .../YYYYMMDD_events.txt

**day**

Optional. Day of observation of the event list. If not entered, program will infer the day from the events.txt file name

**pre**

Optional. This is the header file that contains the setup instructions. Default is pre174.txt. If in another folder, enter the path to it .../pre174.txt

**post**

Optional. This is the footer file that contains the end of observing sequence. Default is post571.txt. If in another folder, enter the path to it .../post571.txt

**out**

Optional. Can use -o or --out. This sets the path for the output scs file. Default will save as YYYYMMDD_174_script.scs and will save in the same location as the program. To set a different path, enter .../YYYYMMDD_174_script.scs





