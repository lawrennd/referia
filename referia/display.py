# Provide compatability with old referia versions by providing referia.data.Data()

from .assess.data import CustomDataFrame
from .config.interface import Interface
from .assess.compute import Compute
from .assess.review import Reviewer
from . import system

from .util.jupyter import expand_cell

def Scorer(index=None, data=None, user_file="_referia.yml", directory="."):
    """
    Return a CustomDataFrame object.

    :param user_file: The name of the user file with interface settings to be loaded in.
    :type user_file: str
    :param directory: The directory to look for the user file in.
    :type directory: str
    :return: The CustomDataFrame object.
    """

    interface = Interface.from_file(user_file=user_file, directory=directory)
    
    if data is None:
        data = CustomDataFrame.from_flow(interface)
    if index is None:
        index = data.index[0]
    sys = system.Sys(interface)
    return Reviewer(index, data, interface, sys)
