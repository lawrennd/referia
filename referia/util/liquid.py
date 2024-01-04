import urllib.parse
import os
from ..util.misc import markdown2html
from liquid.filter import string_filter


@string_filter
def url_escape(string):
    """
    Filter to escape urls for liquid

    :param string: The string to be escaped.
    :type string: str
    :return: The escaped string.
    :rtype: str
    """
    return urllib.parse.quote(string.encode('utf8'))


@string_filter
def markdownify(string):
    """
    Filter to convert markdown to html for liquid"

    :param string: The string to be converted to html.
    :type string: str
    :return: The html.
    :rtype: str
    """
    return markdown2html(string)


@string_filter
def relative_url(string):
    """
    Filter to convert to a relative_url a jupyter notebook under liquid

    :param string: The string to be converted to a relative url.

    :type string: str
    :return: The relative url.
    :rtype: str
    """
    url = os.path.join("/notebooks", string)
    return url


@string_filter
def absolute_url(string):
    """
    Filter to convert to a absolute_url a jupyter notebook under liquid

    :param string: The string to be converted to an absolute url.
    :type string: str
    :return: The absolute url.
    :rtype: str
    """
    # Remove the absolute url from beginning if it exists
    while string[0] == "/":
       string = string[1:]
    return os.path.join("http://localhost:8888/notebooks/", string)


@string_filter
def to_i(string):
    """
    Filter to convert the liquid entry to an integer under liquid.

    :param string: The string to be converted to an integer.
    :type string: str
    :return: The integer value.
    :rtype: int
    """
    if type(string) is str and len(string) == 0:
        return 0
    return int(float(string))
