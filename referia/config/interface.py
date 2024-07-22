import os
import yaml
import json
import numpy as np

from lynguine import access


from lynguine.util.misc import to_valid_var, extract_full_filename, remove_nan
import lynguine

from lynguine.config.context import Context
from lynguine.log import Logger


ctxt = Context()
log = Logger(
    name=__name__,
    level=ctxt._data["logging"]["level"],
    filename=ctxt._data["logging"]["filename"],
)


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

        # create suffices for timestamp columns
        if "modified_suffix" not in data:
            data["modified_suffix"] = "modified"

        if "created_suffix" not in data:
            data["created_suffix"] = "created"

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
                data["review"] = data["scorer"].copy()
                del data["scorer"]
            else:
                raise ValueError("Cannot have both \"scorer\" and \"review\" in the interface.")

        if "review" in data:
            data["review"] = self._expand_review_cluster(data["review"])
            #self._expand_scores()   

        # Extract all fields from the review interface
        review_columns = self._extract_review_write_fields(data)
        for column in review_columns.copy():
            for suffix in [data["modified_suffix"], data["created_suffix"]]:
                timestamp_column = column + "_" + suffix
                if timestamp_column not in review_columns:
                    review_columns.append(timestamp_column)
        
        if "output" in data:
            if "columns" in data["output"]:
                for column in review_columns:
                    if column not in data["output"]["columns"]:
                        log.debug(f"Adding column as \"{column}\" to outputs.")                        
                        data["output"]["columns"].append(column)
            else:
                data["output"]["columns"] = review_columns
                
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
                    
                    #raise ValueError("Got here")
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
                    cluster["filename"] = extract_full_filename(entry["details"])
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
                    tmp = entry.copy()
                    body = tmp["body"]
                    if not isinstance(body, list):
                        body = [body]
                    tmp["children"] = body
                    del tmp["body"]
                    cluster["entries"] = expand_group_review(tmp) # expand loop review only used when start and stop known at run-time.                        
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
        default_ignore = ["compute", "review"]
        viewelem = {"display": 'Parent assesser available <a href="' + os.path.join(os.path.relpath(os.path.expandvars(self._parent._directory), "assessment.ipynb")) + '" target="_blank">here</a>.'}

        # Add links to parent assessment by placing in viewer.
        if "viewer" in self._data:
            if type(self._data["viewer"]) is list:
                self._data["viewer"] = [viewelem] + self._data["viewer"]
            else:
                self._data["viewer"] = [viewelem, self._data["viewer"]]
        else:
            self._data["viewer"] = [viewelem]

            
def expand_load_review(details):
    """
    Extract details from a separate file where they're specified.

    :param details: The details of the scoring element.
    :type details: dict
    """
    # This is a link to a widget specification stored in a file
    if "details" not in details:
        raise ValueError("Load reviewer needs to provide load details as entry under \"details\"")
    df,  newdetails = access.io.read_data(details["details"])
    return_details = []
    for ind, series in df.iterrows():
        return_details.append(remove_nan(series.to_dict()))
    return return_details                      

def expand_group_review(details):
    """
    Extract details that are clustered together in a group.

    :param details: The details of the scoring element.
    :type details: dict
    """
    if "children" not in details:
        raise ValueError("group reviewer needs to provide a list of children under \"children\"")
    return_details = []
    for child in details["children"]:
        if "name" in child and "name" in details and details["name"] is not None:
            child["name"] = details["name"] + "-" + child["name"]
        if "prefix" in details and details["prefix"] is not None:
            if "prefix" in child:
                child["prefix"] = details["prefix"] + child["prefix"]
            if "field" in child:
                child["field"] = details["prefix"] + child["field"]
        return_details.append(child)
    return return_details

def expand_composite_review(details):
    """
    Extract details for a predefined composition of widgets.

    :param details: The details of the scoring element.
    :type details: dict
    """
    if details["type"] == "Criterion":
        value = None
        display = None
        tally = None
        liquid = None
        lis = None
        join = None
        prefix = details["prefix"]
        if "criterion" in details:
            value = details["criterion"]
        if "display" in details:
            display = details["display"]
        if "liquid" in details:
            liquid = details["liquid"]
        if "tally" in details:
            tally = details["tally"]
        if "list" in details:
            lis = details["list"]
        if "join" in details:
            liquid = details["join"]
        if "width" in details:
            width = details["width"]
        else:
            width = "800px"

        criterion = {
            "type": "Markdown",
            "args": {
                "layout": {"width": width},
            }
        }
        if value is not None:
            criterion["args"]["value"] = value
        if display is not None:
            criterion["args"]["display"] = display
        if liquid is not None:
            criterion["args"]["liquid"] = liquid
        if tally is not None:
            criterion["args"]["tally"] = tally
        if join is not None:
            criterion["args"]["join"] = join
        if lis is not None:
            criterion["args"]["list"] = lis
        return [criterion]

    if details["type"] == "CriterionComment":
        criterion = json.loads(json.dumps(details))
        criterion["type"] = "Criterion"
        prefix = details["prefix"]

        if "width" in details:
            width = details["width"]
        else:
            width = "800px"
            
        comment = {
            "field": prefix + " Comment",
            "type": "Textarea",
            "args": {
                "value": "",
                "description": "Comment",
                "layout": {"width": width},
            }
        }
        return [criterion, comment]

    if details["type"] == "CriterionCommentDate":
        criterion = json.loads(json.dumps(details))
        criterion["type"] = "CriterionComment"
        prefix = details["prefix"]
        date = {
            "field": prefix + " Date",
            "type": "DatePicker",
            "args": {
                "description": "Date",
            }
        }
        return [criterion, date]


    if details["type"] == "CriterionCommentRedAmberGreen":
        criterioncomment = json.loads(json.dumps(details))
        criterioncomment["type"] = "CriterionComment"

        prefix = details["prefix"]
        expectation = {
            "field": prefix + " Traffic",
            "type": "Dropdown",
            "args": {
                "placeholder": "Traffic Signal",
                "options": [
                    "",
                    "Red",
                    "Amber",
                    "Green",
                ],
                "description": "Traffic Signal",
            }
        }
        return [criterioncomment, expectation]
    
    if details["type"] == "CriterionCommentRaisesMeetsLowers":
        criterioncomment = json.loads(json.dumps(details))
        criterioncomment["type"] = "CriterionComment"

        prefix = details["prefix"]
        expectation = {
            "field": prefix + " Expectation",
            "type": "Dropdown",
            "args": {
                "placeholder": "Against expectations",
                "options": [
                    "",
                    "Raises",
                    "Meets",
                    "Lowers",
                ],
                "description": "Expectation",
            }
        }
        return [criterioncomment, expectation]

    if details["type"] == "CriterionCommentRaisesMeetsLowersFlag":
        criterioncommentraisesmeetslowers = json.loads(json.dumps(details))
        criterioncommentraisesmeetslowers["type"] = "CriterionCommentRaisesMeetsLowers"

        prefix = details["prefix"]
        flag = {
            "field": prefix + " Flag",
            "type": "Flag",
            "args": {
                "value": False,
                "description": "Flag",
            }
        }
        return [criterioncommentraisesmeetslowers, flag]

    
    if details["type"] == "CriterionCommentScore":
        criterioncomment = json.loads(json.dumps(details))
        criterioncomment["type"] = "CriterionComment"
        if "width" in details:
            width = details["width"]
        else:
            width = "800px"

        prefix = details["prefix"]
        if "min" in details:
            minval = details["min"]
        else:
            minval = 0
        if "max" in details:
            maxval = details["max"]
        else:
            maxval = 10
        if "step" in details:
            step = details["step"]
        else:
            step = 1
        if "value" in details:
            value = details["value"]
        else:
            value = int(((maxval-minval)/2)/step)*step + minval

        slider = {
            "field": prefix + " Score",
            "type": "FloatSlider",
            "args": {
                "min": minval,
                "max": maxval,
                "step": step,
                "value": value,
                "description": "Score",
                "layout": {"width": width},
            }
        }
        return [criterioncomment, slider]
