import os
import re
import string

def file_from_re(pattern: str, directory: str = ".") -> str:
    """
    Extract a filename from a given glob."""
    files = files_from_re(pattern, directory)
    if len(files)>0:
        return files[0]
    else:
        return ""

def files_from_re(pattern: str, directory: str = ".") -> list[str]:
    """
    Extract a filename from a given glob."""

    files = [os.path.join(directory,f) for f in os.listdir(directory) if re.match (pattern, f)]
    return files

def to_valid_file(text):
    """Replace invalid characters with underscore"""
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    text = text.replace("/", "-")
    text = text.replace("\\", "-")
    for c in set(text):
        if c not in valid_chars:
            text = text.replace(c, "_")
    return text


    
