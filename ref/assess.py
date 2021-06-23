import os
import re
from unidecode import unidecode
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import Markdown, display
import ipywidgets as widgets
from ipywidgets import interact, interactive, fixed, interact_manual

from .config import *
from . import access

"""Place commands in this file to assess the data you have downloaded. How are missing values encoded, how are outliers encoded? What do columns represent, makes rure they are correctly labeled. How is the data indexed. Create visualisation routines to assess the data (e.g. in bokeh). Ensure that date formats are correct and correctly timezoned."""

def data():
    outputs = access.outputs()
    additional = access.additional()
    outputs.set_index(outputs['REF output identifier'].apply(lambda x: int(x.replace('O', ''))), inplace=True)
    additional.set_index(additional['REF output identifier'].apply(lambda x: int(x.replace('O', ''))), inplace=True)    
    return outputs.join(additional, rsuffix='additional')

def query(data, index):
    ds = data.loc[index]
    query_score(ds)

def query_score(ds):
    view_record(ds)
    if type(ds["LocalDocumentLink"]) is str:
        os.system('open ' + '--background ' + '"' + os.path.join(config['datadirectory'],ds['LocalDocumentLink']) + '"')
    os.system('open ' + '-a "Google Chrome.app" --background ' + '"' + _search_url(ds) + '"')


def _search_url(ds):
    return unidecode(config['search_url'] + ds['Output title'].replace(' ', '%20'))
    
def view(data):
    """Provide a view of the data that allows the user to verify some aspect of its quality."""
    fig, ax = plt.subplots(figsize=(8, 5))
    data.hist('Score', bins=np.linspace(-.5, 12.5, 14), width=0.8, ax=ax)
    ax.set_xticks(range(0,13))

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



def score(index, df, write_df):
    """Present a paper for assessment"""
    
    comment = {}
    score = {}

    def update_df(df, write_df,
                  o_text, o_score,
                  s_text, s_score,
                  r_text, r_score, interdisciplinary_comment, my_comment, index):
        comment = "{o_text} {o_score} {s_text} {s_score} {r_text} {r_score}".format(o_text=o_text, o_score=o_score, 
                                                                                    s_text=s_text, s_score=s_score, 
                                                                                    r_text=r_text, r_score=r_score)

        score = o_score + s_score + r_score

        # Write index
        write_index = write_df['REF output identifier']=="O" + str(index)
        write_df.at[write_index, 'Comment'] = comment
        write_df.at[write_index, 'Score'] = score
        write_df.at[write_index, 'Comment 2'] = interdisciplinary_comment
        write_df.at[write_index, 'Comment 4'] = my_comment
        filename = os.path.expandvars(os.path.join(config['datadirectory'], config['upload']))
        writer = pd.ExcelWriter(filename, engine='xlsxwriter')
        write_df.to_excel(writer,sheet_name=config['outputs_sheet'], startrow=3,index=False)
        writer.save()
        scored = write_df['Score'].count()
        total = len(write_df['Score'])
        print("Completed {scored} articles from {total} which is {perc:.3g}%".format(scored=scored, total=total, perc=scored/total*100))


    def update_index(df, write_df, index):
        if index not in df.index:
            raise ValueError("Invalid index")

        query(df, index)

        o_text = "O: "
        s_text = "S: "
        r_text = "R: "
        o_score = 2
        s_score = 2
        r_score = 2

        write_index = write_df[write_df['REF output identifier']=="O" + str(index)].index[0]

        print(write_df.at[write_index, 'Comment'])
        if match := re.search('O:\s*(.*)\s*([0-4])\.?\s*S:\s*(.*)\s*([0-4])\.?\s*R:\s*(.*)\s*([0-4])\.?\s*', 
                              write_df.at[write_index, 'Comment']):
            o_text = "O: " + match.group(1).strip()
            s_text = "S: " + match.group(3).strip()
            r_text = "R: " + match.group(5).strip()
            o_score = int(match.group(2))
            s_score = int(match.group(4))
            r_score = int(match.group(6))
        elif len(df['Comment'][index])>0:
            raise ValueError("Could not parse comment section of entry O" + str(index))


        o_score_range = widgets.IntSlider(min=0, max=4, step=1, value=o_score)    
        s_score_range = widgets.IntSlider(min=0, max=4, step=1, value=s_score)    
        r_score_range = widgets.IntSlider(min=0, max=4, step=1, value=r_score)    


        interdisciplinary_comment = write_df['Comment 2'][write_index]
        my_comment = write_df['Comment 4'][write_index]    
        widgets.interact_manual.opts['manual_name'] = 'Save Score'
        scored = write_df['Score'].count()
        total = len(write_df['Score'])
        progress_bar = widgets=IntProgress(value = scored, min=0, max=total, step=1, description="Progress", bar_style="") 
        interact_manual(update_df, o_text=o_text, o_score=o_score_range, 
                        s_text=s_text, s_score=s_score_range, 
                        r_text=r_text, r_score=r_score_range,
                        interdisciplinary_comment=interdisciplinary_comment,
                        my_comment=my_comment, progress_bar=progress_bar,
                        df=fixed(df), index=fixed(index),
                        write_df=fixed(write_df))

    index_select = widgets.Dropdown(options=df.index, value=index)
    interact(update_index, index=index_select, df=fixed(df), write_df=fixed(write_df))



    
def labelled(data):
    """Provide a labelled set of data ready for supervised learning."""
    raise NotImplementedError
