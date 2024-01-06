import os
import re

def most_recent_screen_shot():
    """
    Return the most recent screenshot file name.

    :return: The most recent screenshot file name.
    :rtype: str
    """
    
    directory_name = os.path.expandvars("$HOME/Desktop/")
    files = [f for f in os.listdir(directory_name) 
             if re.match(r"Screenshot [0-9]+-[0-9]+-[0-9]+ at [0-9]+\.[0-9]+\.[0-9]+\.png", f)]
    files.sort()
    
    return files[-1]
