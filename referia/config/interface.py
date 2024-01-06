import os
import yaml
import numpy as np


from ndlpy.util.misc import to_valid_var
import ndlpy


GSPREAD_AVAILABLE=True
try:
    import gspread_pandas.conf as gspdconf
except ImportError:
    GSPREAD_AVAILABILE=False


def nodes(user_file="_referia.yml", directory="."):
    filename = os.path.join(os.path.expandvars(directory), user_file)
    if not os.path.exists(filename):
        return []
    
    with open(filename) as file:
        conf = yaml.load(file, Loader=yaml.FullLoader)

    if "title" in conf:
        key = to_valid_var(conf["title"])
    else:
        key = to_valid_var(directory)

    chain = [(key, directory)]
    if "inherit" in conf:
        chain += nodes(user_file=user_file, directory=conf["inherit"]["directory"]) 
    return chain

    
class Interface(ndlpy.config.interface.Interface):
    def __init__(self, data=None):
        super().__init__(data)

    def __get_item__(self, key):
        """Return local value or inherit from parent"""
        if key not in self._data:
            # key isn't locally available
            if key not in self._parent._ignore:
                return self._parent[key]
            else:
                raise ValueError(f"Key \"{key}\" not found locally and ignored in parent.)")
        else:
            if key in self._parent._append:
                st = self._parent[key]
                if self._data[key] is list:
                    if st is not list:
                        st = [st]
                    return st + self._data[key]
                if self._data[key] is dict:
                    st.update(self._data[key])
                    return st
                if self._data[key] is None:
                    return st
                else:
                    raise ValueError(f"Cannot append to non dictionary or list type for requested key \"{key}\".")

    def get(self, key, default=None):
        """Return local value or inherit from parent"""
        if key not in self._data:
            if key not in self._parent._ignore:
                return self._parent.get(key, default)
            else:
                raise ValueError(f"Key \"{key}\" not found locally and ignored in parent.)")
        else:
            return self.__get_item__(key)

                
    def _process_parent(self):
        if "append" in self._data:
            self._parent._append = self._data["inherit"]["append"]
        else:
            self._parent._append = []
        if "ignore" in self._data:
            self._parent._ignore = self._data["inherit"]["ignore"]
        else:
            self._parent._ignore = []

        default_append = ["additional", "global_consts"]
        for append in default_append:
            if append not in self._parent._ignore and append not in self._parent._append:
                self._parent._append.append(append)

        default_ignore = ["compute", "scorer"]
        for ignore in default_ignore:
            if ignore not in self._parent._append and ignore not in self._parent._ignore:
                self._parent._ignore.append(ignore)
                
        viewelem = {"display": 'Parent assesser available <a href="' + os.path.join(os.path.relpath(os.path.expandvars(self._parent._directory), "assessment.ipynb")) + '" target="_blank">here</a>.'}

        # Add links to parent assessment by placing in viewer.
        if "viewer" in self._data:
            if type(self._data["viewer"]) is list:
                self._data["viewer"] = [viewelem] + self._data["viewer"]
            else:
                self._data["viewer"] = [viewelem, self._data["viewer"]]
        else:
            self._data["viewer"] = [viewelem]

        if not self._parent._writable:
            additional = []
            global_consts = []
            if "scores" in self._parent:
                additional += [self._parent["scores"]] 
                del self._parent["scores"]

            if "series" in self._parent:
                self._parent["series"]["series"] = True
                additional += [self._parent["series"]]
                del self._parent["series"]

            if "globals" in self._parent:
                global_consts += [self._parent["globals"]]
                del self._parent["glibals"]
                
            if len(additional)>0:
                if "additional" not in self._parent:
                    self._parent["additional"] = additional
                else:
                    self._parent["additional"] += additional

            if len(global_consts)>0:
                if "global_consts" not in self._parent:
                    self._parent["global_consts"] = global_consts
                else:
                    self._parent["global_consts"] += global_consts
                    
        del self._data["inherit"]
            

# config = load_config(user_file="_referia.yml", directory=".")

# conf_dir = None
# file_name = "google_secret.json"

# if "google_oauth" in config:
#     if "directory" in config["google_oauth"]:
#         conf_dir = os.path.expandvars(config["google_oauth"]["directory"])
#     if "keyfile" in config["google_oauth"]:
#         file_name = config["google_oauth"]["keyfile"]


# try:
#     config["gspread_pandas"] = gspdconf.get_config(
#         conf_dir=conf_dir,
#         file_name=file_name,
#     )
# except:
#     GSPREAD_AVAILABLE=False
