from matplotlib import pyplot as plt
import numpy as np
import os

three_figsize = (10, 3)
two_figsize = (10, 5)
one_figsize = (5, 5)
big_figsize = (7, 7)
wide_figsize = (7, 3.5)
big_wide_figsize = (10, 6)

def write_figure(filename, figure=None, directory=".", **kwargs):
    """
    Write figure in correct formating

    :param filename: The filename to write to.
    :type filename: str
    :param figure: The figure to write.
    :type figure: matplotlib.figure.Figure
    :param directory: The directory to write to.
    :type directory: str
    :param kwargs: The keyword arguments to pass to savefig.
    :type kwargs: dict
    """
    savename = os.path.join(os.path.expandvars(directory), filename)
    if 'transparent' not in kwargs:
        kwargs['transparent'] = True
    if figure is None:
        plt.savefig(savename, **kwargs)
    else:
        figure.savefig(savename, **kwargs)

def bar_plot(x, height, filename, directory=".", **kwargs):
    """
    Create a bar plot

    :param x: The x values.
    :type x: list
    :param height: The heights of the bars.
    :type height: list
    :param filename: The filename to write to.
    :type filename: str
    :param directory: The directory to write to.
    :type directory: str
    :param kwargs: The keyword arguments to pass to bar.
    :type kwargs: dict
    """
    
    fig, ax = plt.subplots(figsize=big_figsize)
    ax.bar(x, height, **kwargs)
    write_figure(filename, figure=fig, directory=directory)
    plt.close()
    return filename

def histogram(x, filename, directory=".", **kwargs):
    """
    Create a histogram

    :param x: The x values.
    :type x: list
    :param filename: The filename to write to.
    :type filename: str
    :param directory: The directory to write to.
    :type directory: str
    :param kwargs: The keyword arguments to pass to hist.
    :type kwargs: dict
    """
    fig, ax = plt.subplots(figsize=big_figsize)
    ax.hist(x, **kwargs)
    write_figure(filename, figure=fig, directory=directory)
    plt.close()
    return filename
