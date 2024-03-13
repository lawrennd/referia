# Provide compatability with old referia versions by providing referia.data.Data()

from .assess.data import CustomDataFrame
from .config.interface import Interface
from .assess.compute import Compute

def Data(user_file="_referia.yml", directory="."):
    """
    Return a CustomDataFrame object.

    :param user_file: The name of the user file with interface settings to be loaded in.
    :type user_file: str
    :param directory: The directory to look for the user file in.
    :type directory: str
    :return: The CustomDataFrame object.
    """

    interface = Interface.from_file(user_file=user_file, directory=directory)
    data = CustomDataFrame.from_flow(interface)
    return data
