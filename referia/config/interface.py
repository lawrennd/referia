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
    @classmethod
    def default_config_file(cls):
        """
        Return the default configuration file name
        """
        return "_referia.yml"
    
    def __init__(self, data=None):
        """
        Initialise the interface object.

        :param data: The data to be loaded in.
        :type data: dict
        :return: None
        """
        if "allocation" in data:
            allocation = data["allocation"]
            if not isinstance(allocation, list):
                allocation = [allocation]
            if "input" not in data:
                data["input"] = {"type" : "hstack", "specifications" : [{"type": "vstack", "specifications" : allocation}]}
            del data["allocation"]
            
        if "additional" in data:
            additional = data["additional"]
            if not isinstance(additional, list):
                additional = [additional]
            data["input"]["specifications"] += additional
            del data["additional"]

        if "global_consts" in data:
            constants = data["global_consts"]
            if isinstance(constants, list):
                data["constants"] = {"type": "hstack", "specifications": constants}
            else:
                data["constants"] = constants
            del data["global_consts"]

        if "globals" in data:
            parameters = data["globals"]
            if isinstance(parameters, list):
                data["parameters"] = {"type": "hstack", "specifications": parameters}
            else:
                data["parameters"] = parameters
            del data["globals"]

        if "scores" in data:
            data["output"] = data["scores"]
            del data["scores"]

            
            #self._expand_scores()   

        super().__init__(data)
        


                
    def _process_parent(self):

        default_append = ["additional", "global_consts"]
        default_ignore = ["compute", "scorer"]
        viewelem = {"display": 'Parent assesser available <a href="' + os.path.join(os.path.relpath(os.path.expandvars(self._parent._directory), "assessment.ipynb")) + '" target="_blank">here</a>.'}

        # Add links to parent assessment by placing in viewer.
        if "viewer" in self._data:
            if type(self._data["viewer"]) is list:
                self._data["viewer"] = [viewelem] + self._data["viewer"]
            else:
                self._data["viewer"] = [viewelem, self._data["viewer"]]
        else:
            self._data["viewer"] = [viewelem]

            
