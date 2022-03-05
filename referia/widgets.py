import os
import sys
import glob

import IPython
import ipywidgets as ipyw

from pandas.api.types import is_string_dtype, is_numeric_dtype, is_bool_dtype


from .config import *
from .util import notempty, markdown2html
from .log import Logger
from . import display
from . import system


log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)

#other = [jslink, jsdlink, MyCheckbox, MyFileChooser]

list_stateful_widgets = [
    {
        "name" : "IntSlider",
        "function" : ipyw.IntSlider,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "FloatSlider",
        "function" : ipyw.FloatSlider,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Checkbox",
        "function" : ipyw.Checkbox,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Flag",
        "function" : ipyw.Checkbox,
        "default_args" : {},
        "docstr" : None,
        "conversion" : bool,
    },
    {
        "name" : "Text",
        "function" : ipyw.Text,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Textarea",
        "function" : ipyw.Textarea,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Combobox",
        "function" : ipyw.Combobox,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Dropdown",
        "function" : ipyw.Dropdown,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Label",
        "function" : ipyw.Label,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Layout",
        "function" : ipyw.Layout,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "HTML",
        "function" : ipyw.HTML,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "HTMLMath",
        "function" : ipyw.HTMLMath,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
    {
        "name" : "Markdown",
        "function" : ipyw.HTMLMath,
        "default_args" : {},
        "docstr" : None,
        "conversion" : markdown2html,
    },
    {
        "name" : "DatePicker",
        "function" : ipyw.DatePicker,
        "default_args" : {},
        "docstr" : None,
        "conversion" : None,
    },
]

class ReferiaWidget():
    def __init__(self, **args):
        self._parent = None
        self.private = True
        if "function" in args:
            self._ipywidget_function = args["function"]
        else:
            self._ipywidget_function = self._default_widget()

        if "parent" in args:
            self._parent = args["parent"]
        self._create_widget(args)

    def _default_widget(self):
        return ipyw.Button

    def _create_widget(self, args):
        self._ipywidget = self._ipywidget_function(**args)
        self._widget_events()

    def _widget_events(self):
        self._ipywidget.on_click(self.on_click)

    def on_click(self, b):
        pass

    def refresh(self):
        pass

    @property
    def widget(self):
        return self._ipywidget
    
    @property
    def private(self):
        return self._private

    @private.setter
    def private(self, value):
        #if not is_bool_dtype(value):
        #    raise ValueError("Private must be set as bool (True/False)")
        self._private = value

    def display(self):
        IPython.display.display(self._ipywidget)

    def null(self, void):
        pass

    def to_markdown(self):
        return ""
        
class ReferiaStatefulWidget(ReferiaWidget):
    def __init__(self, **args):
        self._conversion = None
        self._viewer = {}
        self._column_name = None
        self._field_name = None
        if "conversion" in args:
            self._conversion = args["conversion"]
            del args["conversion"]
        if "display" in args:
            self._viewer["display"] = args["display"]
            del args["display"]
        if "tally" in args:
            self._viewer["tally"] = args["tally"]
            del args["tally"]
        if "conditions" in args:
            self._viewer["conditions"] = args["conditions"]
            del args["conditions"]
        if "column_name" in args:
            self._column_name = args["column_name"]
            del args["column_name"]
        if "field_name" in args:
            self._field_name = args["field_name"]
            del args["field_name"]
        super().__init__(**args)
        if "value" in args:
            self._default_value = args["value"]
            self.set_value(args["value"])
        else:
            self._default_value = self._ipywidget_function().value
        # Is this a private field (one that doesn't update the parent data)
        if self._field_name is not None and self._field_name[0] == "_": 
            self.private = True
        else:
            self.private = False

        if self.private and "description" not in args: 
            args["descripton"] = " "

    def _default_widget(self):
        return ipyw.Textarea

    def _widget_events(self):
        """Create any relevant wiget event handlers."""
        self._ipywidget.observe(self.on_value_change, names="value")

    def on_value_change(self, value):
        pass
    
    def get_value(self):
        """Get the value of the widget."""
        return self._ipywidget.value

    def get_description(self):
        """Get the value of the widget."""
        return self._ipywidget.description
    
    def set_value(self, value):
        """Set the value of the widget."""
        if notempty(value):
            if self._conversion is None:
                self._ipywidget.value = value
            else:
                self._ipywidget.value = self._conversion(value)
        else:
            self.reset_value()

    def reset_value(self):
        """Reset value to default for widget."""  
        self._ipywidget.value = self._default_value
        
    def get_column(self):
        return self._column_name
    
    def to_markdown(self):
        description = self.get_description()
        value = self.get_value()
        if description is None or description.strip() == "":
            return f"{value}"
        else:
            return f"#### {description}\n\n{value}"
    
class FieldWidget(ReferiaStatefulWidget):
    """Widget for editing field values in parent data."""
    def __init__(self, function=None, conversion=None, **args):
        args["function"] = function
        args["conversion"] = conversion
        super().__init__(**args)
        
    def on_value_change(self, change):
        """When value of the widget changes update the relevant parent data structure."""
        self.set_value(change.new)
        if not self.private and self._parent is not None:
            self._parent.set_column(self.get_column())
            self._parent.set_value(self.get_value())

    def has_viewer(self):
        """Does the widget have a viewer structure for generating its values."""
        return len(self._viewer)>0
    
    def refresh(self):
        """Update the widget value from the data."""
        self._ipywidget.observe(self.null, names='value')
        column = self.get_column()
        if column is not None and self._parent is not None:
            if self.has_viewer():
                value = self._parent._data.viewer_to_value(self._viewer)
                self.set_value(value)
            else:
                self._parent.set_column(column)
                self.set_value(self._parent.get_value())
        else:
            self.reset_value()
        self._ipywidget.observe(self.on_value_change, names="value")
            

class IndexSelector(ReferiaStatefulWidget):
    def __init__(self, parent):
        args = {
            "options": parent.index,
            "value": parent.get_index(),
            "parent" : parent,
            "function" : ipyw.Dropdown,
        }
        super().__init__(**args)

    def on_value_change(self, change):
        self.set_value(change.new)
        if not self.private and self._parent is not None:
            self._parent.set_index(self.get_value())
            system.view_series(self._parent._data)

    def refresh(self):
        pass

class ReferiaMultiWidget(ReferiaStatefulWidget):
    """Class for forming a collection of widgets that interact."""
    def __init__(self, **args):
        pass
    
class FullSelector(ReferiaMultiWidget):
    def __init__(self, parent, stateful_args, stateless_args):
        self._parent = parent
        self._ipywidgets = {}
        for key, item in stateful_args.items():
            item["value"] = item["value_function"]()
            if "options_function" in item:
                item["options"] = item["options_function"]()
            if "display_when_function" in item:
                if "layout" not in item:
                    item["layout"] = {}
                if item["display_when_function"]():
                    item["layout"]["display"] = "block"
                else:
                    item["layout"]["display"] = "none"
        for key, item in stateful_args.items():
            self._ipywidgets[key] = {
                "function": item["function"],
                "result_function": item["result_function"],
                "conversion": item["conversion"],
                }
            del item["function"]
            del item["result_function"]
            self._ipywidgets[key]["set_value"] = gsv_(key, item, self)
            
            self._ipywidgets[key]["widget"] = self._ipywidgets[key]["function"](**item)
            self._ipywidgets[key]["update"] = gwu_(key, item, self)

        for key, item in self._ipywidgets.items():
            self._ipywidgets[key]["on_change"] = gwc_(key, item, self)            
            self._ipywidgets[key]["widget"].observe(self._ipywidgets[key]["on_change"], names="value")


        for key, item in stateless_args.items():
            self._ipywidgets[key] = {
                "function": item["function"],
                "on_click_function": item["on_click_function"],
            }
            del item["function"]
            del item["on_click_function"]
            self._ipywidgets[key]['widget'] = self._ipywidgets[key]["function"](**item)
            self._ipywidgets[key]["widget"].on_click(gocf_(key, item, self))

    def display(self):
        objects = []
        for key, item in self._ipywidgets.items():
            objects.append(item["widget"])
        IPython.display.display(ipyw.VBox(objects))

    

class IndexSubIndexSelectorSelect(FullSelector):
    def __init__(self, parent):
        # Define the widgets to create
        stateful_args = {
            "index_select":  {
                "options_function": parent.get_indices,
                "value_function": parent.get_index,
                "function": ipyw.Dropdown,
                "result_function" : parent.set_index,
                "conversion": None,
            },
            "selector_select":  {
                "function": ipyw.Dropdown,
                "options_function": parent.get_selectors,
                "value_function": parent.get_selector,
                "result_function": parent.set_selector,
                "display_when_function": parent.get_select_selector,
                "conversion": None,
            },
            "subindex_select": {
                "function" : ipyw.Dropdown,
                "options_function": parent.get_subindices,
                "value_function": parent.get_subindex,
                "result_function" : parent.set_subindex,
                "display_when_function": parent.get_select_subindex,
                "conversion": None,
            },
            "select_subindex_checkbox": {
                "function" : ipyw.Checkbox,
                "value_function": parent.get_select_subindex,
                "result_function": parent.set_select_subindex,
                "conversion": bool,
                "description": "Select Subindex",
            },
            "select_selector_checkbox": {
                "function" : ipyw.Checkbox,
                "value_function": parent.get_select_selector,
                "result_function": parent.set_select_selector,
                "conversion": bool,
                "description": "Select Selector",
            }
        }
        stateless_args = {
            "generate_button" : {
                "function": ipyw.Button,
                "on_click_function": parent.add_new_row_to_series,
                "description": "Add Row",
            }
        }
        super().__init__(parent, stateful_args, stateless_args)

def gocf_(key, item, obj, docstr=None):
    """Generator function for on_click function for the button class."""
    def on_click(b):
        obj._ipywidgets[key]["on_click_function"]()
        for other_key, widget in obj._ipywidgets.items():
            if other_key == key:
                pass
            elif "update" in widget:
                    widget["update"]()
    return on_click
            
def gsv_(key, item, obj, docstr=None):
    """Generator function for a set value function for the multiwidget class"""
    def set_value(value):
        if notempty(value):
            if obj._ipywidgets[key]["conversion"] is None:
                obj._ipywidgets[key]["widget"].value = value
            else:
                obj._ipywidgets[key]["widget"].value = obj._ipywidgets[key]["conversion"](value)
        else:
            obj._ipywidgets[key]["widget"].value = self._ipywidgets[key]["function"]().value
        # Perform callback to set the result.
        obj._ipywidgets[key]["result_function"](obj._ipywidgets[key]["widget"].value)
    set_value.__docstr__ = docstr
    return set_value

def gwc_(key, item, obj, docstr=None):
    """Generator functions for propagating changes to other widgets on this change."""
    name = "on_" + key + "_change"
    def on_change(change):
        obj._ipywidgets[key]["set_value"](change.new)
        for other_key, widget in obj._ipywidgets.items():
            if other_key == key:
                pass
            elif "update" in widget:
                widget["update"]()
    on_change.__name__ = name
    on_change.__docstr__ = docstr
    return on_change
                    
def gwu_(key, item, obj, docstr=None):
    """Generator function for making update calls for a given widget."""
    def on_other_widgets_change():
        widg = obj._ipywidgets[key]["widget"]
        if "options_function" in item:
            log.debug(f"Updating widget \"{key}\" options.")
            widg.options = item["options_function"]()
        if "value_function" in item:
            log.debug(f"Updating widget \"{key}\" value.")
            widg.value = item["value_function"]()
        if "display_when_function" in item:
            if item["display_when_function"]():
                widg.layout.display = "block"
            else:
                widg.layout.display = "none"
        on_other_widgets_change.__name__ = key
        on_other_widgets_change.__docstr__ = docstr
    return on_other_widgets_change

def gwf_(name, function, conversion=None, default_args={}, docstr=None):
    """This function wraps the widget function and calls it with any additional default arguments as specified."""
    def widget_function(**args):
        all_args = default_args.copy()
        all_args.update(args)
        return FieldWidget(
            function=function,
            conversion=conversion,
            **all_args,
        )
    widget_function.__name__ = name
    widget_function.__docstr__ = docstr
    return widget_function

def populate_widgets(list_stateful_widgets):
    """populate_widgets: Automatically creates widget wrapper objects and adds them to the module."""
    this_module = sys.modules[__name__]
    for widget in list_stateful_widgets:
        setattr(
            this_module,
            widget["name"],
            gwf_(**widget),
        )

def MyFileChooser(**args):
    """Create a simple Dropdown box to allow file selection from a given path."""
    if "directory" not in args:
        directory = "."
    else:
        directory = args["directory"]

    if "path" in args:
        directory = os.path.join(path, directory)
        
    if "glob" not in args:
        globname = "*"
    else:
        globname = args["glob"]
    files = glob.glob(os.path.join(os.path.expandvars(directory), globname))
    dirs = []
    options = []
    for option in [''] + dirs + files:
        options.append(os.path.basename(option))
    args["options"] = options
    
    return ipyw.Dropdown(**args)



def interact(function, **args):
    newargs = {}
    for key, widget in args.items():
        newargs[key] = widget.widget
    ipyw.interact(function, **newargs)

def interact_manual(function, **args):
    newargs = {}
    for key, widget in args.items():
        newargs[key] = widget.widget
    ipyw.interact_manual(function, **newargs)

def interactive(function, **args):
    newargs = {}
    for key, widget in args.items():
        newargs[key] = widget.widget
    ipyw.interactive(function, **newargs)


fixed = ipyw.fixed
class CreateDocButton(ReferiaWidget):
    """Create a document for editing based on the information we have."""
    def __init__(self, **args):
        args["description"] = "Create " + args["type"]
        super().__init__(**args)
        self.type = args["type"]
        self.document = args["document"]
        
    def on_click(self, b):
        self._parent.create_document(self.document)
    
        
class SaveButton(ReferiaWidget):
    """Write the data to the appropriate storage files."""
    def __init__(self, **args):
        args["description"] = "Save Flows"
        super().__init__(**args)

    def on_click(self, b):
        self._parent.save_flows()

class ReloadButton(ReferiaWidget):
    def __init__(self, **args):
        args["description"] = "Reload Flows"
        super().__init__(**args)

    def on_click(self, b):
        self._parent.load_flows()

    
populate_widgets(list_stateful_widgets)

