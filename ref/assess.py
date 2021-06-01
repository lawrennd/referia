import os
import numpy as np
from .config import *
from IPython.display import Markdown, display


from . import access

"""Place commands in this file to assess the data you have downloaded. How are missing values encoded, how are outliers encoded? What do columns represent, makes rure they are correctly labeled. How is the data indexed. Crete visualisation routines to assess the data (e.g. in bokeh). Ensure that date formats are correct and correctly timezoned."""

def data():
    outputs = access.outputs()
    additional = access.additional()
    outputs = outputs.set_index(outputs['REF output identifier'].apply(lambda x: int(x.replace('O', ''))))
    additional = additional.set_index(additional['REF output identifier'].apply(lambda x: int(x.replace('O', ''))))    
    return outputs.join(additional, rsuffix='additional')

def query(data, index):
    ds = data.loc[index]
    query_score(ds)

def query_score(ds):
    view_record(ds)
    os.system('open ' + '--background ' + '"' + os.path.join(config['datadirectory'],ds['LocalDocumentLink']) + '"')
    os.system('open ' + '-a "Google Chrome.app" --background ' + '"' + config['search_url'] + ds['Output title'].replace(' ', '%20') + '"')


def view(data):
    """Provide a view of the data that allows the user to verify some aspect of its quality."""
    data.hist('Score', bins=np.linspace(-.5, 12.5, 14), width=0.8)

def view_record(ds):
    """Print a view of a single record."""
    if ds['Interdisciplinary'] == 'Yes':
        prefix = "**Interdisciplinary**: "
    else:
        prefix = ""

    display(Markdown("""
### {prefix}{title}

{volume}

### {year}, {cites}
    
{additional}
""".format(prefix=prefix,
           volume = ds['Volume title'],
           title=ds['Output title'], 
           year=str(ds['Year']), 
           cites=ds['Citation count'], 
           additional=ds['Additional output information'])))
    
    
def labelled(data):
    """Provide a labelled set of data ready for supervised learning."""
    raise NotImplementedError
