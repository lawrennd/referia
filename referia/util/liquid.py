import urllib.parse
import os
import referia.util.misc 
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
    try:
        return urllib.parse.quote(string.encode('utf8'))
    except UnicodeEncodeError:
        raise ValueError("String encoding to UTF-8 failed")

@string_filter
def markdownify(string):
    """
    Filter to convert markdown to html for liquid

    :param string: The string to be converted to html.
    :type string: str
    :return: The html.
    :rtype: str
    """
    try:
        return referia.util.misc.markdown2html(string)
    except Exception as e:
        raise ValueError(f"Error converting markdown to HTML: {e}")

@string_filter
def relative_url(string):
    """
    Filter to convert to a relative_url a jupyter notebook under liquid

    :param string: The string to be converted to a relative url.
    :type string: str
    :return: The relative url.
    :rtype: str
    """
    return urllib.parse.urljoin("/notebooks/", string.lstrip('/'))

@string_filter
def absolute_url(string):
    """
    Filter to convert to an absolute_url a jupyter notebook under liquid

    :param string: The string to be converted to an absolute url.
    :type string: str
    :return: The absolute url.
    :rtype: str
    """
    base_url = "http://localhost:8888/notebooks/"
    # Remove leading slashes to avoid urljoin treating the path as absolute
    return urllib.parse.urljoin(base_url, string.lstrip('/'))

@string_filter
def to_i(string):
    """
    Filter to convert the liquid entry to an integer under liquid.

    :param string: The string to be converted to an integer.
    :type string: str
    :return: The integer value.
    :rtype: int
    """
    try:
        if string:
            return int(float(string))
        return 0
    except ValueError:
        raise ValueError(f"Invalid input for conversion to integer: '{string}'")
