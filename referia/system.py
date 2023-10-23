import os
import re

from unidecode import unidecode


import filecmp
from shutil import copy2, move
import tempfile
import random
import string

import pyminizip as pz

import pypdftk as tk

from .log import Logger
from .util import to_camel_case, notempty, markdown2html, extract_full_filename, extract_abs_filename, renderable, tallyable
from .fileutil import to_valid_file
from . import config
from . import access
from . import assess
from . import display
from . import util

import platform
OSX = False
if platform.system() == "Darwin":
    OSX=True
    import appscript as ap
    import mactypes as mt
import pathlib as pl

if OSX:
    class Outlook(object):
        def __init__(self):
            self.client = ap.app("Microsoft Outlook")

if OSX:
    class GoogleChrome(object):
        def __init__(self):
            self.client = ap.app("Google Chrome")

if OSX:
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


class Sys():
    def __init__(self, user_file="_referia.yml", directory="."):
        self._directory = directory
        self._config = config.load_config(user_file=user_file,
                                          directory=directory)

        self._log = Logger(
            name=__name__,
            level=self._config["logging"]["level"],
            filename=self._config["logging"]["filename"]
        )
        self._tmp_pdf_files = {}


    def clear_temp_files(self):
        delete_keys = []
        for filename, values in self._tmp_pdf_files.items():
            destname = os.path.join(values["tmpdirectory"], filename)
            delete_keys.append(filename)
            if os.path.exists(destname):
                self._log.info(f"Removing temporary file \"{filename}\".")
                os.remove(destname)

        for key in delete_keys:
            del self._tmp_pdf_files[key]

    def open_localfile(self, filename):
        """Open a local file."""
        if os.path.isdir(filename):
            self.open_directory(filename)
            return

        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext == ".pdf":
            self.open_pdf(filename)
        elif ext == ".ipynb":
            self.open_ipynb(filename)
        elif ext == ".mp4":
            self.open_video(filename)
        elif ext == ".py":
            self.open_python(filename)
        elif ext == ".docx":
            self.open_docx(filename)
        elif ext == ".md" or ext == ".markdown":
            self.open_markdown(filename)
        else:
            self._log.debug(f"Opening file \"{filename}\".")
            os.system(f"open --background \"{filename}\"")


    def open_directory(self, filename):
        """Use the system viewer to open a directory.""" 
        self._log.debug(f"Opening file \"{filename}\".")
        os.system(f"open --background \"{filename}\"")

    def open_markdown(self, filename):
        """Use the system viewer to open a markdown file."""
        self._log.debug(f"Opening file \"{filename}\".")
        os.system(f"open --background \"{filename}\"")

    def open_python(self, filename):
        """Use the system viewer to open a python file."""
        self._log.debug(f"Opening file \"{filename}\".")
        os.system(f"open --background \"{filename}\"")

    def open_docx(self, filename):
        """Use the system viewer to open a python file."""
        self._log.debug(f"Opening file \"{filename}\".")
        os.system(f"open --background \"{filename}\"")

    def open_ipynb(self, filename):
        """Use the system viewer to open a python file."""
        self._log.debug(f"Opening file \"{filename}\".")
        os.system(f"open --background \"{filename}\"")

    def open_pdf(self, filename):
        """Use the system viewer to open a PDF."""
        self._log.debug(f"Opening file \"{filename}\".")
        os.system(f"open --background \"{filename}\"")

    def open_video(self, filename):
        """Use the system viewer to open a video."""
        self._log.debug(f"Opening file \"{filename}\".")
        os.system(f"open --background \"{filename}\"")

    def open_url(self, urlname):
        """Use the browser to open URL."""
        if "browser" in self._config:
            browser=self._config["browser"]
        else:
            browser="Google Chrome.app" 

        self._log.debug(f"Opening url \"{urlname}\".")
        os.system(f"open -a \"{browser}\" --background \"{urlname}\"")


    def create_document(self, document, **args):
        """Create a document based on the data we have."""
        doctype = document["type"]
        if doctype == "docx":
            self.create_docx(document, **args)
        if doctype == "email":
            self.create_email(document, **args)
        if doctype == "excel":
            self.create_excel(document, **args)
        if doctype == "markdown":
            self.create_markdown(document, **args)
        if doctype == "letter":
            self.create_letter(document, **args)
        if doctype == "formlink":
            self.create_formlink(document, **args)


    def create_summary(self, details, **args):
        """Create a summary file based on the data in all fields."""
        doctype = details["type"]
        if doctype == "zip":
            self.create_zip(details, **args)

    def create_summary_document(self, document, **args):
        """Create a summary document based on the data in all fields."""
        doctype = document["type"]
        if doctype == "docx":
            self.create_docx(document, **args)
        if doctype == "email":
            self.create_email(document, **args)
        if doctype == "excel":
            self.create_excel(document, **args)
        if doctype == "markdown":
            self.create_markdown(document, **args)
        if doctype == "letter":
            self.create_letter(document, **args)

    def create_zip(self, details, **args):
        """Create a zip file based on the files listed."""
        zip_args = {}
        zip_args["filename"] = extract_full_filename(details["store"])
        if "password" in details:
            zip_args["password"] = details["password"]
        else:
            zip_args["password"] = None
        zip_args["filelist"] = args["entries"]

        self.write_zip(**zip_args)


    def create_email(self, document, **args):
        """Create an email based on the data we have."""
        email_args = {}
        if "content" in args:
            email_args["body"] = markdown2html(args["content"])
        if "title" in args:
            email_args["subject"] = args["title"]
        if "attach" in args:
            margs = {"filename": args["attach"]}
            email_args["attach"] = extract_full_filename(margs)

        for recips in ["to", "cc", "bcc"]:
            if recips in args:
                email_args[recips] = args[recips]
        if "to" in email_args:
            to = email_args["to"]
        else:
            to = "unknown address"
        self._log.debug(f"Drafting email to \"{to}\".")
        self.draft_email(**email_args)


    def create_document_content(self, document, **args):
        """Create the content for the documents."""
        filename = extract_full_filename(args)
        if "content" in args:
            content = args["content"]
        else:
            content = ""
        data = {}
        for key, item in args.items():
            if key not in ["filename", "directory", "content"]:
                data[key] = item
        return data, filename, content

    def create_docx(self, document, **args):
        """Create a Microsoft word style document."""
        data, filename, content = self.create_document_content(document, **args)
        access.write_docx_file(data=data, filename=filename, content=content)
        self.open_localfile(filename)

    def create_markdown(self, document, **args):
        """Create a markdown document."""
        data, filename, content = self.create_document_content(document, **args)
        access.write_markdown_file(data=data, filename=filename, content=content)
        self.open_localfile(filename)

    def create_letter(self, document, **args):
        """Create a markdown letter."""
        data, filename, content = self.create_document_content(document, **args)
        access.write_letter_file(data=data, filename=filename, content=content)
        self.open_localfile(filename)

    def create_formlink(self, document, **args):
        """Write a form link (url)."""
        data, filename, content = self.create_document_content(document, **args)
        access.write_formlink(data=data, filename=filename, content=content)
        self.open_localfile(filename)


    def write_zip(self, filename=None, password=None, filelist=None, directorylist=[], compress=4):
        """Write a zip file using pyminizip"""
        pz.compress_multiple(filelist, directorylist, filename, password, compress)


    # Email scripts originally from https://stackoverflow.com/questions/61529817/automate-outlook-on-mac-with-python
    def draft_email(self, subject="", body="", to=[], cc=[], bcc=[], attach=[]):
        """Draft an email for sending."""
        if type(attach) is not list:
            attach = [attach]
        if type(to) is not list:
            to = [to]
        if type(cc) is not list:
            cc = [cc]
        if type(bcc) is not list:
            bcc = [bcc]
        to = [ele for ele in to if ele != ""]
        cc = [ele for ele in cc if ele != ""]
        bcc = [ele for ele in bcc if ele != ""]
        attach = [ele for ele in attach if ele != ""]


        msg = Message(subject=subject, body=body, to_recip=to, cc_recip=cc, bcc_recip=bcc)

        # attach file
        for a in attach:
            p = pl.Path(a)
            msg.add_attachment(p)

        msg.show()

    def move_file(self, origfile, destfile):
        """Move a file for editing or viewing."""
        if os.path.exists(origfile):
            self._log.debug(f"Moving \"{origfile}\" to \"{destfile}\"")
            self.move(origfile, destfile)
        else:
            raise ValueError(f"\"{origfile}\" doesn't exist in move_file.")

    def copy_file(self, origfile, destfile, view=None, data=None):
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
                    self._log.debug(f"Extracting \"{destfile}\" from \"{origfile}\" pages {firstpage}-{lastpage}")
                    tk.get_pages(
                        pdf_path=origfile,
                        ranges=[[firstpage,
                                 lastpage]],
                        out_file=destfile,
                    )
            else:
                self._log.debug(f"Copying \"{origfile}\" to \"{destfile}\".")
                copy2(origfile, destfile)
        else:
            self._log.warning(f"Warning edit file \"{origfile}\" does not exist.")

    def move_screen_capture(self, filename, order=0):
        """Copy the most recent screen capture to a given location."""
        if "capture_directory" in self._config:
            capture_directory = os.path.expandvars(self._config["capture_directory"])
        else:
            capture_directory = os.path.expandvars("$HOME/Desktop")
        # set the regular expression pattern
        if "capture_pattern" in self._config:
            capture_pattern = self._config["capture_pattern"]
        else:    
            capture_pattern = r'^Screenshot \d{4}-\d{2}-\d{2} at \d{2}\.\d{2}\.\d{2}\.png$'

        # compile the regular expression pattern
        regex = re.compile(capture_pattern)

        # use a list comprehension to search for files in the directory that match the regular expression
        matching_files = [file_name for file_name in os.listdir(capture_directory) if regex.search(file_name)]

        # sort the list of matching file names alphabetically
        matching_files.sort(reverse=True)
        self.move_file(os.path.join(capture_directory, matching_files[order]), filename)


    def edit_files(self, data):
        """Use the system viewer to show a PDF containing relevant information to the assessment."""

        displays = []
        if "editpdf" in self._config:
            displays += self._config["editpdf"]

        for view in displays:
            val = self.extract_field_value(view, data)
            if "storedirectory" in view:
                storeDirectory = os.path.expandvars(view["storedirectory"])
            else:
                raise ValueError(f"Missing \"storedirectory\" in edit_files configuration.")
            if "sourcedirectory" in view:
                sourceDirectory = os.path.expandvars(view["sourcedirectory"])
            else:
                raise ValueError(f"Missing \"sourcedirectory\" in edit_files configuration.")
            if "name" in view:
                filestub = view["name"] + ".pdf"
            elif renderable(view):
                filestub = data.view_to_tmpname(view) + ".pdf"
            else:
                print(view)
                filestub = ''.join(random.choices(string.digits+string.ascii_letters, k=8)) + ".pdf"

            
            if isinstance(val, list):
                vals = val
            else:
                vals = [val]
            for i, val in enumerate(vals):
            
                if type(val) is str:

                    # Filename to edit, based on index of the file plus the stub
                    editfilename = to_valid_file(str(data.get_index()))
                    if len(vals)>1:
                        editfilename += "_" + str(enumerate)
                    editfilename += "_" + to_valid_file(filestub)
                    destfile = os.path.join(storeDirectory, editfilename)
                    if not os.path.exists(storeDirectory):
                        os.makedirs(storeDirectory)
                    origfile = os.path.join(sourceDirectory,val)
                        
                    if not os.path.exists(destfile):
                        self.copy_file(origfile, destfile, view, data)
                    self.open_localfile(destfile)
                else:
                    tyval = type(val)
                    self._log.warning(f"Expected \"val\" to be of type str actual type is \"{tyval}\"")

    def view_directory(self, view):
        """View a directory containing relevant information to the assessment."""
        raise NotImplementedError("view_directory not yet implemented.")

    def extract_file(self, view, data):
        """Extract information from a given file returning it as a string."""
        if "source" in view:
            filename = data.get_value_column(view["source"])

        if os.path.exists(filename):
            if "extractor" in view:
                extractor = view["extractor"]
                if extractor == "pdfannots":
                    return subprocess.run(["pdfannots", filename], capture_output=True)
        self._log.warning(f"Unknown extractor in {view}.")

    def extract_field_value(self, view, data):
        """Extract the field value """
        if renderable(view):
            val = data.view_to_value(view)
            tmpname = data.view_to_tmpname(view)
        elif tallyable(view):
            val = data.tally_to_value(view)
            tmpname = data.tally_to_tmpname(view)
        elif "field" in view:
            val = data.get_value_column(view["field"])
            tmpname = to_camel_case(view["field"])        
        elif "file" in view:
            val = view["file"]
        else:
            raise ValueError(f"Missing \"field\", \"file\", renderable or tallyable section in the extract field value configuration.")
        return val
        
    def view_file(self, view, data):
        """View a file containing relevant information to the assessment."""
        filename = ""
        tmpname = ''.join(random.choices(string.digits+string.ascii_letters, k=8))
        temp_file = False
        if "temp_file" in view:
            temp_file = view["temp_file"]
        val = self.extract_field_value(view, data)

        if "directory" in view:
            directory = view["directory"]
        else:
            directory = "" # If display is a full path, placing "." here messes it up
        # If it's a list view them all.
        if isinstance(val, list):
            vals = val
        else:
            vals = [val]
        for val in vals:
            if type(val) is str:
                filename = os.path.expandvars(os.path.join(directory,val))
            else:
                self._log.warning(f"Provided file {val} is not in string form.")

            if os.path.exists(filename):
                _, ext = os.path.splitext(filename)
                if temp_file:
                    tmpdirectory = tempfile.gettempdir()
                    destfile = str(data.get_index()) + "_" + tmpname + ext
                    destname = os.path.join(tmpdirectory, destfile)
                    if not os.path.exists(destname):
                        self._log.debug(f"Copying \"{filename}\" to \"{destname}\".")
                        copy2(filename, destname)
                    self._tmp_pdf_files[destfile] = {
                        "origfile": filename,
                        "tmpdirectory": tmpdirectory,
                    }
                    self.open_localfile(destname)
                else:
                    self.open_localfile(filename)
            else:
                self._log.warning(f"view_file \"{filename}\" does not exist.")


    def view_files(self, data):
        """Use the system viewer to show a PDF containing relevant information to the assessment."""
        displays = []
        if "localpdf" in self._config:
            displays += self._config["localpdf"]
        if "localvideo" in self._config:
            displays += self._config["localvideo"]
        if "localipynb" in self._config:
            displays += self._config["localipynb"]
        if "localdocx" in self._config:
            displays += self._config["localdocx"]
        if "localdirectory" in self._config:
            displays += self._config["localdirectory"]

        for view in displays:
            self.view_file(view, data)


    def view_urls(self, data):
        """View any urls that are provided."""
        displays = []
        if "urls" in self._config:
            displays += self._config["urls"]

        for view in displays:
            if "url" in view:
                if "field" in view:
                    val = data.get_value_column(view["field"])
                else:
                    val = None
                if "field" in view and type(val) is str:
                    urlterm = val
                elif renderable(view):
                    urlterm = data.view_to_value(view)
                elif tallyable(view):
                    urlterm = data.tally_to_value(view)
                else:
                    urlterm = ""
                urlname = unidecode(view["url"] + urlterm.replace(" ", "%20"))
                self.open_url(urlname)




