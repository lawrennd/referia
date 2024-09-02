# Being done in assess currently, needs to be moved here.

import os

import re

import pandas as pd
import liquid as lq

import datetime

from .config import *
from .log import Logger
from .util import to_camel_case, remove_nan, renderable, tallyable, markdown2html

log = Logger(
    name=__name__,
    level=config["logging"]["level"],
    filename=config["logging"]["filename"]
)

@string_filter
def url_escape(string):
    """Filter to escape urls for liquid"""
    return urllib.parse.quote(string.encode('utf8'))


@string_filter
def mymarkdownify(string):
    """Filter to convert markdown to html for liquid"""
    return markdown2html(string.encode("utf8")).encode("utf8")

@string_filter
def relative_url(string):
    """Filter to convert to a relative_url a jupyter notebook under liquid"""
    return os.path.join("/notebooks", string.encode("utf8"))

@string_filter
def base_url(string):
    """Filter to convert to a relative_url a jupyter notebook under liquid"""
    return os.path.join("http://localhost:8888/notebooks/", string.encode("utf8"))



class Render():
    """
    Render a view from a data frame.

    The Render object is used to render a view from a data frame. The view is a dictionary
    that specifies how to render the data frame. The view can include liquid templates
    and other renderable fields.

    :param data: The data frame to render.
    :type data: pd.DataFrame
    """
    def __init__(self, data):
        """Initialize the Render object."""
        self._data = data

        # Create a Liquid environment
        self._liquid_env = lq.Liquid()
        self._liquid_env.register_filter(url_escape)
        self._liquid_env.register_filter(mymarkdownify)
        self._liquid_env.register_filter(relative_url)
        self._liquid_env.register_filter(base_url)
        
    
    def _default_mapping(self):
        """Generate the default mapping from config or from columns"""
        # If a mapping is provided in _referia.yml use it, otherwise generate
        if "mapping" in config:
            mapping = config["mapping"]
        else:
            mapping = automapping(self.columns)
        return mapping

    def mapping(self, mapping=None, series=None):
        """Generate dictionary of mapping between variable names and column values."""
        if mapping is None:
            mapping = self._default_mapping()

        format = {}
        for key, column in mapping.items():
            if series is not None:
                if column in series:
                    format[key] = series[column]                    
            else:
                self._data.set_column(column)
                format[key] = self._data.get_value()

        return remove_nan(format)
    
    def viewer_to_value(self, viewer, kwargs=None):
        """Convert a viewer structure to populated values."""
        value = ""
        if type(viewer) is not list:
            viewer = [viewer]
        for view in viewer:
            value += self.view_to_value(view, kwargs)
            if value != "":
                value += "\n\n"
        return value

    def view_to_value(self, view, kwargs=None):
        """Create the text of the view."""
        value = ""

        if self.conditions(view):
            if type(view) is dict:
                if "list" in view:
                    values = []
                    for v in view["list"]:
                        values.append(self.view_to_value(v, kwargs))
                    return values
                if "join" in view:
                    if "list" not in view["join"]:
                        log.warning("No field \"list\" in \"concat\" viewer.")
                    elements = self.view_to_value(view["join"], kwargs)
                    if "separator" in view["join"]:
                        sep = view["join"]["separator"]
                    else:
                        sep = "\n\n"
                    return sep.join(elements)
                if "liquid" in view:
                    value += self.liquid_to_value(view["liquid"], kwargs)
                if "tally" in view:
                    value += self.tally_to_value(view["tally"], kwargs)
                if "display" in view:
                    value += self.display_to_value(view["display"], kwargs)
                return value
            else:
                raise TypeError("View should be a \"dict\".")
        else:
            return None

    def summary_viewer_to_value(self, viewer, kwargs=None):
        """Convert a summary viewer structure to populated values."""
        value = ""
        if type(viewer) is not list:
            viewer = [viewer]
        for view in viewer:
            value += self.summary_view_to_value(view, kwargs)
            if value != "":
                value += "\n\n"
        return value
    
    def summary_view_to_value(self, view, kwargs=None):
        """Create the text of the summary view."""
        value = ""

        if self.conditions(view):
            if type(view) is dict:
                if "list" in view:
                    values = []
                    for v in view["list"]:
                        values.append(self.view_to_value(v, kwargs))
                    return values
                if "join" in view:
                    if "list" not in view["join"]:
                        log.warning("No field \"list\" in \"concat\" viewer.")
                    elements = self.view_to_value(view["join"], kwargs)
                    if "separator" in view["join"]:
                        sep = view["join"]["separator"]
                    else:
                        sep = "\n\n"
                    return sep.join(elements)
                if "liquid" in view:
                    value += self.liquid_to_value(view["liquid"], kwargs)
                if "tally" in view:
                    value += self.tally_to_value(view["tally"], kwargs)
                if "display" in view:
                    value += self.display_to_value(view["display"], kwargs)
                return value
            else:
                raise TypeError("View should be a \"dict\".")
        else:
            return None

    def view_to_tmpname(self, view):
        """Convert a view to a temporary name"""
        if "list" in view:
            name = "list_"
            for v in view["list"]:
                name += self.view_to_tmpname(v)
                name += "_"
            return name
        elif "join" in view:
            name = "join_"
            if "list" not in view["join"]:
                log.warning("No field \"list\" in \"concat\" viewer.")
            name += self.view_to_tmpname(view["join"])
            return name
        elif "liquid" in view:
            name = self.liquid_to_tmpname(view["liquid"])
            return name
        elif "display" in view:
            name = self.display_to_tmpname(view["display"])
            return name

    def tally_to_value(self, tally, kwargs=None):
        """
        Create the text of the view.

        A tally view has a `begin`, `end`, and `display` field. The `begin` and `end` fields
        are optional. The `display` field is required. The `display` field is a view
        that is repeated for subindices in the data frame. The `begin` and `end`
        fields are views that are displayed once at the beginning and end of the
        tally view, respectively.

        The `begin`, `end`, and `display` fields can include liquid template variables.

        The subindices from the dataframe are determined by the `which` field in the
        tally dictionary. The following options are available for the `which` key:

        - pop: The first subindex.
        - bottom: The last subindex.
        - previous: The subindex before the current one.
        - next: The subindex after the current one.
        - earlier: All subindices before the current one.
        - later: All subindices after the current one.
        - others: All subindices except the current one.
        - all: All subindices.

        If no `which` key is provided, all subindices are returned.

        :param tally: The tally view.
        :type tally: dict
        :return: The text of the tally view.
        :rtype: str
        """
        return self.tally_values(tally, kwargs)

    def tally_to_tmpname(self, tally):
        """Convert a view to a temporary name"""
        if "tally" in view:
            name = self.tally_to_tmpname(view["tally"])
        return name

    def conditions(self, view):
        """
        Check if a given viewer should be displayed.

        The viewer can have a "conditions" field that contains a list of conditions. Each
        condition can have a "present" field that contains a "field" key. If the field
        is not present in the data frame, the viewer is not displayed. Each condition
        can also have an "equal" field that contains a "field" key and a "value" key. If
        the field is not equal to the value, the viewer is not displayed.
        
        :param view: The viewer to check.
        :type view: dict
        :return: Whether the viewer should be displayed.
        :rtype: bool        
        """
        if "conditions" not in view:
            return True
        else:
            for condition in view["conditions"]:
                if "present" in condition:
                    if not condition["present"]["field"] in self._data.columns:
                        return False
                    else:
                        self._data.set_column(condition["present"]["field"])
                        if pd.isna(self._data.get_value()):
                            return False
                        else:
                            return True

                if "equal" in condition:
                    self._data.set_column(condition["equal"]["field"])
                    if not self._data.get_value() == condition["equal"]["value"]:
                        return False
        return True

    def display_to_tmpname(self, display):
        """Convert a display string to a temp name"""
        return to_camel_case(display.replace("/", "_").replace("{","").replace("}", ""))


    def display_to_value(self, display, kwargs=None):
        """
        Render a 'format' display template.

        :param display: The display template.
        :type display: str
        :param kwargs: The keyword arguments to be passed to the template.
        :type kwargs: dict
        :return: The rendered template.
        :rtype: str
        """
        if kwargs is None:
            kwargs = self.mapping()
        try:
            return display.format(**kwargs)
        except KeyError as err:
            raise KeyError(f"The mapping doesn't contain the key \"{err}\" requested in \"{display}\". Set the mapping in \"_referia.yml\".") from err

    def liquid_to_tmpname(self, display):
        """Convert a display string to a temp name"""
        return to_camel_case(display.replace("/", "_").replace("{","").replace("}", "").replace("%","-"))

    def liquid_to_value(self, display, kwargs=None):
        """
        Render a liquid template.

        :param display: The liquid template.
        :type display: str
        :param kwargs: The keyword arguments to be passed to the template.
        :type kwargs: dict
        :return: The rendered template.
        :rtype: str
        """
        
        if kwargs is None:
            kwargs = self.mapping()
        try:
            return self._liquid_env.from_string(display).render(**remove_nan(kwargs))
        except Exception as err:
            raise Exception(f"In {display}\n\n {err}") from err

    def tally_to_tmpname(self, tally):
        """Convert a tally to a temporary name"""
        tmpname = ""
        if "begin" in tally:
            tmpname += "begin_"
            tmpname += self.view_to_tmpname(tally["begin"])
        tmpname += "display_"
        tmpname += self.view_to_tmpname(tally)
        if "end" in tally:
            tmpname += "end_"
            tmpname += self.view_to_tmpname(tally["end"])
        return tmpname

    def tally_values(self, tally, kwargs=None):
        """
        Create the text of the tally view.

        A tally view has a `begin`, `end`, and `display` field. The `begin` and `end` fields
        are optional. The `display` field is required. The `display` field is a view
        that is repeated for subindices in the data frame. The `begin` and `end`
        fields are views that are displayed once at the beginning and end of the
        tally view, respectively.

        The `begin`, `end`, and `display` fields can include liquid template variables.
        

        The subindices from the dataframe are determined by the `which` field in the
        tally dictionary. The following options are available for the `which` key:

        - pop: The first subindex.
        - bottom: The last subindex.
        - previous: The subindex before the current one.
        - next: The subindex after the current one.
        - earlier: All subindices before the current one.
        - later: All subindices after the current one.
        - others: All subindices except the current one.
        - all: All subindices.

        If no `which` key is provided, all subindices are returned.

        :param tally: The tally view.
        :type tally: dict
        :return: The text of the tally view.
        :rtype: str
        """
        value = ""
        if "begin" in tally:
            value += tally["begin"]
            if value != "":
                value += "\n\n"
        orig_subindex = self._data.get_subindex()
        subindices = self.tally_series(tally)
        for subindex in subindices:
            self._data.set_subindex(subindex)
            value += self.view_to_value(tally, kwargs)
            if value != "":
                value += "\n\n"
        self._data.set_subindex(orig_subindex)
        if "end" in tally:
            value += tally["end"]
            if value != "":
                value += "\n\n"
        return value

    def tally_series(self, tally):
        """
        Return a series of subindices to be tallied.

        A tally dictionary can specify which subindices to tally. The following
        options are available for the "which" key in the tally dictionary:

        - pop: The first subindex.
        - bottom: The last subindex.
        - previous: The subindex before the current one.
        - next: The subindex after the current one.
        - earlier: All subindices before the current one.
        - later: All subindices after the current one.
        - others: All subindices except the current one.
        - all: All subindices.

        If no "which" key is provided, all subindices are returned.

        :param tally: The tally dictionary.
        :type tally: dict
        :return: The series of subindices.
        :rtype: pd.Series
        """
        orig_subindex = self._data.get_subindex()
        subindices = self._data.get_subindices()
        if subindices is None:
            return None
        if orig_subindex in subindices:
            cur_loc = subindices.get_loc(orig_subindex)
        else:
            cur_loc = 0
            orig_subindex = subindices[0]
        def subind_val(ind):
            try:
                return pd.Index([subindices[ind]])
            except IndexError as e:
                log.info(f"Requested invalid index in Data.tally_series()")
                return pd.Index([subindices[cur_loc]])

        def subind_series(ind, starter=True, reverse=False):
            try:
                if starter:
                    return pd.Index(subindices[ind:])
                else:
                    return pd.Index(subindices[:ind])

            except IndexError as e:
                log.info(f"Requested invalid index in Data.tally_series()")
                if starter:
                    return pd.Index(subindices[cur_loc:])
                else:
                    return pd.Index(subindices[:cur_loc])

        if "reverse" not in tally or not tally["reverse"]:
            reverse=False
        else:
            reverse=True
            
        if "which" not in tally:
            return subindices
        elif tally["which"] == "pop":
            return subind_val(0, reverse=reverse)
        elif tally["which"] == "bottom":
            return subind_val(-1, reverse=reverse)
        elif tally["which"] == "previous":
            return subind_val(cur_loc+1, reverse=reverse)
        elif tally["which"] == "next":
            return subind_val(cur_loc-1, reverse=reverse)
        elif tally["which"] == "earlier":
            return subind_series(cur_loc+1, reverse=reverse)
        elif tally["which"] == "later":
            return subind_series(cur_loc, starter=False, reverse=reverse)
        elif tally["which"] == "others":
            return subind_series(cur_loc, starter=False, reverse=reverse).append(subind_series(cur_loc+1))
        elif tally["which"] == "all":
            return subindices
        else:
            raise ValueError("Unrecognised subindices specifier in tally.")
    
    def _column_from_renderable(self, df, **kwargs):
        """Create a column from a renderable field."""
        return self._series_from_renderable(df, is_index=False, **kwargs)


    def _index_from_renderable(self, df, **kwargs):
        """Create an index from a renderable field."""
        return self._series_from_renderable(df, is_index=True, **kwargs)

    def _series_from_value(self, df, value, name, **kwargs):
        """Create a series from a given value."""
        series = pd.Series(index=df.index, dtype="object")
        for index in series.index:
            series[index] = value
        return series        

    def _series_from_renderable(self, df, is_index=False, index_col=None, **kwargs):
        """Extract a series from a renderable dictionary."""
        series = pd.Series(index=df.index, dtype="object")
        for index in series.index:
            if not is_index and len(self._data.columns)>0:
                self._data.set_index(index)
            kwargs2 = self.mapping(series=df.loc[index])
            series[index] = self.view_to_value(kwargs, kwargs2)
        return series
    
    def _series_from_regexp_of_field(self, df, source, regexp, name, **kwargs):
        """Extract a series from data frame field and regular expression."""
        series = pd.Series(index=df.index, dtype="object")
        for index in series.index:
            try:
                sourcetext = df.at[index, source]
            except KeyError as err:
                raise KeyError(f"Could not find the source field, \"{err}\", listed in _referia.yml under name: \"{name}\" in the DataFrame.")
            match = re.match(
                regexp,
                sourcetext,
            )
            if match:
                if len(match.groups())>1:
                    log.warning(f"Multiple regular expression matches in \"{regexp}\".")
                series[index] = match.group(1)
            else:
                log.warning(f"No match of regular expression \"{regexp}\" to \"{source}\".")
        return series
    
