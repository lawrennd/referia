import os
import yaml
import numpy as np


from lynguine.util.misc import to_valid_var, extract_full_filename
import lynguine

from referia.assess.review import expand_group_review, expand_composite_review, expand_load_review

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

    
class Interface(lynguine.config.interface.Interface):
    @classmethod
    def default_config_file(cls):
        """
        Return the default configuration file name
        """
        return "_referia.yml"
    
    def __init__(self, data=None):
        """
        Initialise the interface object. The referia interface is converted to a linguine interface.

        :param data: The data to be loaded in.
        :type data: dict
        :return: None
        """
        if "allocation" in data:
            allocation = data["allocation"]
            mapping, columns = self._extract_mapping_columns(allocation)
            if "mapping" in allocation:
                del allocation["mapping"]
            if "columns" in allocation:
                del allocation["columns"]

                
            if isinstance(allocation, list):
                index = None
                for i, item in enumerate(allocation):
                    if "index" in item:
                        if index is None:
                            index = item["index"]
                        elif index != item["index"]:
                            errmsg = "All \"allocation\" items must have the same \"index\"."
                            log.error(errmsg)
                            raise ValueError(errmsg)
                        del item["index"]
                        allocation[i] = item
            else:
                if "index" in allocation:
                    index = allocation["index"]
                del allocation["index"]
                allocation = [allocation]
                
            # If "input" is not present, create it with the list of allocation.
            if "input" not in data:
                data["input"] = {
                    "type" : "hstack", # allocation will be concatenated horizontally with additionals
                    "index" : index, # extracted index from allocation elements
                    "specifications" : [{ 
                        "type": "vstack", # each allocation element will be concatenated vertically
                        "specifications" : allocation
                    }],
                }
            else:
                errmsg = "\"allocation\" is not allowed when \"input\" is present."
                log.error(errmsg)
                raise ValueError(errmsg)
            if "mapping" in data["input"]:
                data["input"]["mapping"] += mapping
            else:
                data["input"]["mapping"] = mapping
            if "columns" in data["input"]:
                data["input"]["columns"] += columns
            else:
                data["input"]["columns"] = columns
            del data["allocation"]
            
        if "additional" in data:
            additional = data["additional"]
            mapping, columns = self._extract_mapping_columns(additional)
            if "mapping" in additional:
                del additional["mapping"]
            if "columns" in additional:
                del additional["columns"]
            if not isinstance(additional, list):
                additional = [additional]
            data["input"]["specifications"] += additional
            if "mapping" in data["input"]:
                data["input"]["mapping"] += mapping
            else:
                data["input"]["mapping"] = mapping
            if "columns" in data["input"]:
                data["input"]["columns"] += columns
            else:
                data["input"]["columns"] = columns
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

        if "scorer" in data:
            if "review" not in data:
                data["review"] = data["scorer"]
            else:
                raise ValueError("Cannot have both \"scorer\" and \"review\" in the interface.")

        if "review" in data:
            data["review"] = self._expand_review_cluster(data["review"])
            
            #self._expand_scores()   

        super().__init__(data)
        
    @classmethod
    def _expand_review_cluster(cls, review):
        """
        Expand the review section of the interface into a lynguine form.

        :param review: The review section of the interface.
        :type review: dict
        :return: The expanded review section.
        :rtype: dict
        """
        expanded_review = []
        for entry in review:
            cluster = {}
            if "type" in entry:
                if entry["type"] == "group":
                    cluster["type"] = "group"
                    cluster["entries"] = expand_group_review(entry)
                elif entry["type"] in [
                        "Criterion",
                        "CriterionComment",
                        "CriterionCommentDate",
                        "CriterionCommentRedAmberGreen",
                        "CriterionCommentRaisesMeetsLowers",
                        "CriterionCommentRaisesMeetsLowersFlag",
                        "CriterionCommentScore"
                ]:
                    cluster["type"] = "composite"
                    cluster["entries"] = expand_composite_review(entry)                    
                elif entry["type"] == "load":
                    cluster["type"] = "load"
                    cluster["filename"] = extract_full_filename(entry)
                    cluster["entries"] = expand_load_review(entry)
                elif entry["type"] == "loop":
                    cluster["type"] = "loop"
                    if "start" in entry:
                        cluster["start"] = entry["start"]
                    else:
                        raise ValueError("Missing start entry in loop")                        
                    if "stop" in entry:
                        cluster["stop"] = entry["stop"]
                    else:
                        raise ValueError("Missing stop entry in loop")
                    if "step" in entry:
                        cluster["step"] = entry["step"]
                    cluster["entries"] = expand_group_review(entry) # expand loop review only used when start and stop known at run-time.                        
                else:
                    cluster = entry
            # Call recursively to expand the review section.      
            if "entries" in cluster:
                cluster["entries"] = cls._expand_review_cluster(cluster["entries"])
            expanded_review.append(cluster)
            
        return expanded_review
    
    def _extract_mapping_columns(self, data):
        """
        Extract mapping and columns from data.

        :param data: The data to be processed.
        :type data: dict
        :return: The mapping and columns.
        :rtype: tuple
        """
        mapping = {}
        columns = []
        if "mapping" in data:
            mapping = data["mapping"]
            del data["mapping"]
        if "columns" in data:
            columns = data["columns"]
            del data["columns"]
        return mapping, columns
                
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

            
