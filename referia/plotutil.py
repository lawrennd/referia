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
    """Write figure in correct formating"""
    savename = os.path.join(os.path.expandvars(directory), filename)
    if 'transparent' not in kwargs:
        kwargs['transparent'] = True
    if figure is None:
        plt.savefig(savename, **kwargs)
    else:
        figure.savefig(savename, **kwargs)

def bar_plot(x, heights, filename, directory=".", **kwargs):
    fig, ax = plt.subplots(figsize=big_figsize)
    ax.bar(values, **kwargs)
    write_figure(filename, figure=fig, directory=directory)
    plt.close()
    return filename

def histogram(x, filename, directory=".", **kwargs):
    fig, ax = plt.subplots(figsize=big_figsize)
    ax.hist(x, **kwargs)
    write_figure(filename, figure=fig, directory=directory)
    plt.close()
    return filename
