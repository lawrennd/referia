import os

from unidecode import unidecode


import filecmp
from shutil import copy2
import tempfile

from .config import *
from .log import Logger
from . import access
from . import assess

TMPPDFFILES={}

log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)

def clear_temp_files():
    delete_keys = []
    for filename, values in TMPPDFFILES.items():
        destname = os.path.join(values["tmpdirectory"], filename)
        delete_keys.append(filename)
        if os.path.exists(destname):
            log.info(f"Removing temporary file \"{filename}\".")
            os.remove(destname)

    for key in delete_keys:
        del TMPPDFFILES[key]

def open_localfile(filename):
    """Open a local file."""
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext == ".pdf":
        open_pdf(filename)
    elif ext == ".mp4":
        open_video(filename)
    elif ext == ".py":
        open_python(filename)
    elif ext == ".md" or ext == ".markdown":
        open_markdown(filename)
    else:
        log.info(f"Opening file \"{filename}\".")
        os.system(f"open --background \"{filename}\"")


def open_markdown(filename):
    """Use the system viewer to open a markdown file."""
    log.info(f"Opening file \"{filename}\".")
    os.system(f"open --background \"{filename}\"")

def open_python(filename):
    """Use the system viewer to open a python file."""
    log.info(f"Opening file \"{filename}\".")
    os.system(f"open --background \"{filename}\"")
    
def open_pdf(filename):
    """Use the system viewer to open a PDF."""
    log.info(f"Opening file \"{filename}\".")
    os.system(f"open --background \"{filename}\"")

def open_video(filename):
    """Use the system viewer to open a video."""
    log.info(f"Opening file \"{filename}\".")
    os.system(f"open --background \"{filename}\"")
    
def open_url(urlname):
    """Use the browser to open URL."""
    if "browser" in config:
        browser=config["browser"]
    else:
        browser="Google Chrome.app" 
    
    log.info(f"Opening url \"{urlname}\".")
    os.system(f"open -a \"{browser}\" --background \"{urlname}\"")

def copy_file(origfile, destfile, display, data):
    """Copy a file, or pages from it, for separate editing or viewing."""
    _, ext = os.path.splitext(origfile)
    ext = ext.lower()

    if os.path.exists(origfile):
        if ext == ".pdf" and "pages" in display and "first" in display["pages"] and "last" in display["pages"]:
            # Extract pages from a PDF
            firstpage = data.get_current_value(display["pages"]["first"])
            lastpage = data.get_current_value(display["pages"]["last"])
            if assess.notempty(firstpage) and assess.notempty(lastpage) and assess.notempty(display["field"]):
                firstpage = int(firstpage)
                lastpage = int(lastpage)
                log.info(f"Extracting \"{destfile}\" from \"{origfile}\" pages {firstpage}-{lastpage}")
                tk.get_pages(
                    pdf_path=origfile,
                    ranges=[[firstpage,
                             lastpage]],
                    out_file=destfile,
                )
        else:
            log.info(f"Copying \"{origfile}\" to \"{destfile}\".")
            copy2(origfile, destfile)
    else:
        log.warning(f"Warning edit file \"{origfile}\" does not exist.")


def edit_files(data):
    """Use the system viewer to show a PDF containing relevant information to the assessment."""

    displays = []
    if "editpdf" in config:
        displays += config["editpdf"]
        
    for display in displays:
        if "field" in display:
            val = data.get_current_value(display["field"])
        if type(val) is str:
            storedirectory = os.path.expandvars(display["storedirectory"])
            origfile = os.path.join(os.path.expandvars(display["sourcedirectory"]),val)
            if "name" in display:
                filestub = display["name"] + ".pdf"
            else:
                filestub = to_camel_case(display["field"]) + ".pdf"
            editfilename = str(data.get_current_value(config["allocation"]["index"])) + "_" + filestub
            destfile = os.path.join(storedirectory,editfilename)
            if not os.path.exists(storedirectory):
                os.makedirs(storedirectory)
            if not os.path.exists(destfile):
                copy_file(origfile, destfile, display, data)
            open_localfile(destfile)


def view_directory(display):
    """View a directory containing relevant information to the assessment."""
    pass

def view_file(display, data):
    """View a file containing relevant information to the assessment."""
    filename = ""
    tmpname = ""
    if "field" in display:
        val = data.get_current_value(display["field"])
        if type(val) is str:
            filename = os.path.expandvars(os.path.join(display["directory"],val))
            tmpname = to_camel_case(display["field"])
    elif "file" in display:
        filename = os.path.expandvars(os.path.join(display["directory"], display["file"]))
    if os.path.exists(filename):
        _, ext = os.path.splitext(filename)
        if len(tmpname)>0:
            tmpdirectory = tempfile.gettempdir()
            destfile = str(data.get_current_value(config["allocation"]["index"])) + "_" + tmpname + ext
            destname = os.path.join(tmpdirectory, destfile)
            if not os.path.exists(destname):
                log.debug(f"Copying \"{filename}\" to \"{destname}\".")
                copy2(filename, destname)
            TMPPDFFILES[destfile] = {
                "origfile": filename,
                "tmpdirectory": tmpdirectory,
            }
            open_localfile(destname)
        else:
            open_localfile(filename)
    else:
        log.warning(f"view_file \"{filename}\" does not exist.")
    
    
def view_files(data):
    """Use the system viewer to show a PDF containing relevant information to the assessment."""
    displays = []
    if "localpdf" in config:
        displays += config["localpdf"]
    if "localvideo" in config:
        displays += config["localvideo"]

    for display in displays:
        view_file(display, data)
            
                
def view_urls(data):
    """View any urls that are provided."""
    displays = []
    if "urls" in config:
        displays += config["urls"]
        
    for display in displays:
        if "url" in display:
            if "field" in display:
                val = data.get_current_value(display["field"])
            else:
                val = None
            if "field" in display and type(val) is str:
                urlterm = val
            elif "display" in display:
                urlterm = display.view_to_text(display, data)
            else:
                urlterm = ""
            urlname = unidecode(display["url"] + urlterm.replace(" ", "%20"))
            open_url(urlname)


def view_series(data):
    clear_temp_files()
    view_files(data)
    view_urls(data)
    edit_files(data)


