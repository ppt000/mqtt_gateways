'''
The default configuration settings in a single string constant.

Given how the configuration loader works, only the sections and options
declared already here will be considered in any external configuration file.
If an external configuration file is read and contains sections and options not
included in here, they will be ignored, except for the ``[INTERFACE]`` section.
The section ``[INTERFACE]`` is reserved to the configuration parameters that might be
needed by the interface being implemented.

Use this declaration as a template configuration file.
'''

CONFIG = '''
# See notes on file paths at the end
[CONFIG]
# Placeholder used by the loader to return the location where the configuration settings are coming from, or an error
[INTERFACE]
# Placeholder for whatever is needed by the gateway interface
[MQTT]
# The parameters to connect to the MQTT broker
host: 127.0.0.1
port: 1883
keepalive: 60
# This is the timeout of the 'loop()' call in the MQTT library
timeout: 0.01
# The 'root' of all the topics
root: home
# The reconnection is attempted every 'reconnect_delay' seconds
#reconnect_delay: 30
# Maximum number of reconnection attempts
#max_reconnect_attempts: 120
# Map file. Default name is <*application_name*.map>.
mapfilename: data/
[LOG]
# All logs above and including WARN are sent to syslog or equivalent, to log below that a file location is needed.
# Log file. Default name is <*application_name*.log>. Make sure the process will have the rights to it.
logfilename: data/
# Turn debug 'on' if logging of all debug messages is required, otherwise its INFO
debug: off
# Email credentials; leave empty if not required
# for example: host: 127.0.0.1
host:
# for example: port: 25
port:
# for example: address: me@example.com
address:

# Note on file paths (or file names):
#   - the default name is 'application_name' + default extension (.log, .map, ... etc);
#   - the default path is the 'application' directory, which 'should' be the location of the launching script;
#   - file paths can be empty in which case the default name and path will be used;
#   - file paths can be directory only (ends with a '/') and are appended with the default name;
#   - file paths can be absolute or relative; absolute start with a '/' and relative are prepended with the default directory;
#   - file 'paths' can be file only (no '/' whatsoever) and are prepended with the default directory;
#   - use forward slashes '/' in any case, even for Windows systems, it should work;
#   - however for Windows systems, use of the drive letter might be an issue and has not been tested.
'''