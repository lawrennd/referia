import os

from unidecode import unidecode


import filecmp
from shutil import copy2
import tempfile

import pypdftk as tk

from .config import *
from .log import Logger
from .util import to_camel_case, notempty, markdown2html, extract_full_filename
from . import access
from . import assess
from . import display

import appscript as ap
import mactypes as mt
import pathlib as pl



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
    elif ext == ".ipynb":
        open_ipynb(filename)
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

def open_ipynb(filename):
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


class Outlook(object):
    def __init__(self):
        self.client = ap.app("Microsoft Outlook")

class GoogleChrome(object):
    def __init__(self):
        self.client = ap.app("Google Chrome")

def create_document(document, **args):
    """Create a document based on the data we have."""
    doctype = document["type"]
    if doctype == "email":
        create_email(document, **args)
    if doctype == "docx":
        create_docx(document, **args)
    if doctype == "markdown":
        create_markdown(document, **args)

def create_email(document, **args):
    """Create an email based on the data we have."""
    email_args = {}
    if "content" in args:
        email_args["body"] = markdown2html(args["content"])
    if "title" in args:
        email_args["subject"] = args["title"]
    if "filename" in args:
        email_args["attach"] = extract_full_filename(args)
        
    for recips in ["to", "cc", "bcc"]:
        if recips in args:
            email_args[recips] = args[recips]
    if "to" in email_args:
        to = email_args["to"]
    else:
        to = "unknown address"
    log.info(f"Drafting email to \"{to}\".")
    draft_email(**email_args)

def create_docx(document, **args):
    pass

def create_markdown(document, **args):
    """Create a markdown document."""
    filename = extract_full_filename(args)
    if "content" in args:
        content = args["content"]
    else:
        content = ""
    data = {}
    for key, item in args.items():
        if key not in ["filename", "directory"]:
            data[key] = item
    access.write_markdown_file(data=data, filename=filename)
    open_localfile(filename)
            
    
# Email scripts originally from https://stackoverflow.com/questions/61529817/automate-outlook-on-mac-with-python
def draft_email(subject="", body="", to=[], cc=[], bcc=[], attach=None):
    """Draft an email for sending."""
    msg = Message(subject=subject, body=body, to_recip=to, cc_recip=cc, bcc_recip=bcc)

    # attach file
    if attach is not None:
        p = pl.Path(attach)
        msg.add_attachment(p)

    msg.show()


class Message(object):
    
    def __init__(self, parent=None, subject="", body="", to_recip=[], cc_recip=[], bcc_recip=[], show_=False):

        if parent is None: parent = Outlook()
        client = parent.client

        self.msg = client.make(
            new=ap.k.outgoing_message,
            with_properties={ap.k.subject: subject, ap.k.content: body})

        if len(to_recip)>0:
            self.add_recipients(emails=to_recip, type_='to')
        if len(cc_recip)>0:
            self.add_recipients(emails=cc_recip, type_='cc')
        if len(bcc_recip)>0:
            self.add_recipients(emails=bcc_recip, type_='bcc')
        if show_: self.show()

    def show(self):
        self.msg.open()
        self.msg.activate()

    def add_attachment(self, p):
        # p is a pl.Path() obj, could also pass string

        p = mt.Alias(str(p)) # convert string/path obj to POSIX/mactypes path

        attach = self.msg.make(new=ap.k.attachment, with_properties={ap.k.file: p})

    def add_recipients(self, emails, type_='to'):
        if not isinstance(emails, list): emails = [emails]
        for email in emails:
            self.add_recipient(email=email, type_=type_)

    def add_recipient(self, email, type_='to'):
        msg = self.msg

        if type_ == 'to':
            recipient = ap.k.to_recipient
        elif type_ == 'cc':
            recipient = ap.k.cc_recipient

        msg.make(new=recipient,
                 with_properties={ap.k.email_address: {ap.k.address: email}})

    
def copy_file(origfile, destfile, view, data):
    """Copy a file, or pages from it, for separate editing or viewing."""
    _, ext = os.path.splitext(origfile)
    ext = ext.lower()

    if os.path.exists(origfile):
        if ext == ".pdf" and "pages" in view and "first" in view["pages"] and "last" in view["pages"]:
            # Extract pages from a PDF
            firstpage = data.get_value_column(view["pages"]["first"])
            lastpage = data.get_value_column(view["pages"]["last"])
            if notempty(firstpage) and notempty(lastpage) and notempty(view["field"]):
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
        
    for view in displays:
        if "field" in view:
            val = data.get_value_column(view["field"])
        if type(val) is str:
            storedirectory = os.path.expandvars(view["storedirectory"])
            origfile = os.path.join(os.path.expandvars(view["sourcedirectory"]),val)
            if "name" in view:
                filestub = view["name"] + ".pdf"
            else:
                filestub = to_camel_case(view["field"]) + ".pdf"
            editfilename = str(data.get_value_column(config["allocation"]["index"])) + "_" + filestub
            destfile = os.path.join(storedirectory,editfilename)
            if not os.path.exists(storedirectory):
                os.makedirs(storedirectory)
            if not os.path.exists(destfile):
                copy_file(origfile, destfile, view, data)
            open_localfile(destfile)


def view_directory(view):
    """View a directory containing relevant information to the assessment."""
    pass

def view_file(view, data):
    """View a file containing relevant information to the assessment."""
    filename = ""
    tmpname = ""
    if "field" in view:
        val = data.get_value_column(view["field"])
        if type(val) is str:
            filename = os.path.expandvars(os.path.join(view["directory"],val))
            tmpname = to_camel_case(view["field"])
    elif "file" in view:
        filename = os.path.expandvars(os.path.join(view["directory"], view["file"]))
    if os.path.exists(filename):
        _, ext = os.path.splitext(filename)
        if len(tmpname)>0:
            tmpdirectory = tempfile.gettempdir()
            destfile = str(data.get_index()) + "_" + tmpname + ext
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
    if "localipynb" in config:
        displays += config["localipynb"]

    for view in displays:
        view_file(view, data)
            
                
def view_urls(data):
    """View any urls that are provided."""
    displays = []
    if "urls" in config:
        displays += config["urls"]
        
    for view in displays:
        if "url" in view:
            if "field" in view:
                val = data.get_value_column(view["field"])
            else:
                val = None
            if "field" in view and type(val) is str:
                urlterm = val
            elif "display" in view:
                urlterm = data.view_to_value(view)
            else:
                urlterm = ""
            urlname = unidecode(view["url"] + urlterm.replace(" ", "%20"))
            open_url(urlname)


def view_series(data):
    clear_temp_files()
    view_files(data)
    view_urls(data)
    edit_files(data)


