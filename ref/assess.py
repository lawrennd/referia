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
    outputs.set_index(outputs['REF output identifier'].apply(lambda x: int(x.replace('O', '').replace('o', ''))), inplace=True)
    additional.set_index(additional['REF output identifier'].apply(lambda x: int(x.replace('O', '').replace('o', ''))), inplace=True)    
    return outputs.join(additional, rsuffix='additional')

def case_study_data():
    case_studies = access.case_studies()
    additional = access.additional_case_studies()
    case_studies.set_index(case_studies['REF case study identifier'].apply(lambda x: int(x.replace('i', ''))), inplace=True)
    additional.set_index(additional['REF case study identifier'].apply(lambda x: int(x.replace('i', ''))), inplace=True)    
    return case_studies.join(additional, rsuffix='additional')

def query(data, index):
    ds = data.loc[index]
    query_score(ds)

    
def query_score(ds):
    view_record(ds)
    if type(ds["LocalDocumentLink"]) is str:
        os.system('open ' + '--background ' + '"' + os.path.join(config['datadirectory'],ds['LocalDocumentLink']) + '"')
    os.system('open ' + '-a "Google Chrome.app" --background ' + '"' + _search_url(ds) + '"')


def _search_url(ds):
    if 'Output title' in ds.index:
        title = ds['Output title']
    elif 'Case study title' in ds.index:
        title = ds['Case study title']
    return unidecode(config['search_url'] + title.replace(' ', '%20'))
    
def view(data):
    """Provide a view of the data that allows the user to verify some aspect of its quality."""
    fig, ax = plt.subplots(figsize=(8, 5))
    data.hist('Score', bins=np.linspace(-.5, 12.5, 14), width=0.8, ax=ax)
    ax.set_xticks(range(0,13))

def view_record(ds):
    """Print a view of a single record."""
    if 'Interdisciplinary' in ds.index and ds['Interdisciplinary'] == 'Yes':
        prefix = "**Interdisciplinary**: "
    else:
        prefix = ""

    if 'Volume title' in ds.index:
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

    elif 'Case study title' in ds.index:
        display(Markdown("""
### {title}

{covid_statement}

""".format(prefix=prefix,
           title = ds['Case study title'],
           covid_statement=ds['COVID-19 statement'])))

def score(index, df, write_df):
    """Present a paper for assessment"""
    
    comment = {}
    score = {}

    def update_df(df, write_df,
                  o_text=fixed('None'), o_score=fixed(0),
                  s_text=fixed('None'), s_score=fixed(0),
                  r_text=fixed('None'), r_score=fixed(0),
                  interdisciplinary_comment=fixed(''),
                  my_comment=fixed(''),
                  index=fixed(0)):
        if 'Case study title' in df.columns:
            comment = "{r_text} {r_score} {s_text} {s_score}".format(r_text=r_text, r_score=r_score, s_text=s_text, s_score=s_score)
            score = (r_score + s_score)/2
            # Write index
            write_index = write_df['REF case study identifier']=="i" + str(index)
            write_df.at[write_index, 'Comment 1'] = comment
            write_df.at[write_index, 'Score'] = score
            write_df.at[write_index, 'Comment 4'] = my_comment
            write_df.at[write_index, 'Comment 5'] = pd.to_datetime('today') 
            
        else:
            comment = "{o_text} {o_score} {s_text} {s_score} {r_text} {r_score}".format(o_text=o_text, o_score=o_score, 
                                                                                        s_text=s_text, s_score=s_score, 
                                                                                        r_text=r_text, r_score=r_score)

            score = o_score + s_score + r_score

            # Write index
            write_index = write_df['REF output identifier']=="o" + str(index)

            write_df.at[write_index, 'Comment'] = comment
            write_df.at[write_index, 'Score'] = score
            write_df.at[write_index, 'Comment 2'] = interdisciplinary_comment
            write_df.at[write_index, 'Comment 4'] = my_comment
            write_df.at[write_index, 'Accept DW'] = pd.to_datetime('today') 

        filename = os.path.expandvars(os.path.join(config['datadirectory'], config['upload']))
        
        writer = pd.ExcelWriter(filename, engine='xlsxwriter', datetime_format="YYYY-MM-DD HH:MM:SS")
        if 'Case study title' in df.columns:
            sheet_name=config['case_study_sheet']
        else:
            sheet_name=config['outputs_sheet']
        write_df.to_excel(writer,sheet_name=sheet_name, startrow=3,index=False)
        writer.save()


    def update_index(df, write_df, index):
        if index not in df.index:
            raise ValueError("Invalid index")

        query(df, index)

        scored = write_df['Score'].count()
        total = len(write_df['Score'])
        remain = total - scored
        progress_label = "{remain} to go. Scored {scored} from {total} which is {perc:.3g}%".format(remain=remain, scored=scored, total=total, perc=scored/total*100)
        

        if 'Case study title' in df.columns:
            r_text = "R: "
            s_text = "S: "
            r_score = 2
            s_score = 2
            write_index = write_df[write_df['REF case study identifier']=="i" + str(index)].index[0]

            print(write_df.at[write_index, 'Comment 1'])
            print(progress_label)
            
            if match := re.search('R:\s*(.*)\s*([0-4])\.?\s*S:\s*(.*)\s*([0-4])\.?\s*', 
                                  write_df.at[write_index, 'Comment 1']):
                r_text = "R: " + match.group(1).strip()
                s_text = "S: " + match.group(3).strip()
                r_score = int(match.group(2))
                s_score = int(match.group(4))

            elif len(df['Comment 1'][index])>0:
                raise ValueError("Could not parse comment section of entry i" + str(index))
            r_score_range = widgets.IntSlider(min=0, max=4, step=1, value=r_score)    
            s_score_range = widgets.IntSlider(min=0, max=4, step=1, value=s_score)    
    
            my_comment = write_df['Comment 4'][write_index]    
            progress_bar = widgets.IntProgress(value = scored, min=0, max=total, step=1, description="Progress", bar_style="")
            widgets.interact_manual.opts['manual_name'] = 'Save Score'

            interact_manual(update_df,
                            progress_bar=progress_bar,
                            progress_label=progress_label,
                            r_text=r_text,
                            r_score=r_score_range,
                            s_text=s_text,
                            s_score=s_score_range, 
                            my_comment=my_comment,
                            df=fixed(df), index=fixed(index),
                            write_df=fixed(write_df))


        else:
            o_text = "O: "
            s_text = "S: "
            r_text = "R: "
            o_score = 2
            s_score = 2
            r_score = 2

            write_index = write_df[write_df['REF output identifier']=="o" + str(index)].index[0]

            print(write_df.at[write_index, 'Comment'])
            print(progress_label)
            
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
            progress_bar = widgets.IntProgress(value = scored, min=0, max=total, step=1, description="Progress", bar_style="")
            widgets.interact_manual.opts['manual_name'] = 'Save Score'

            interact_manual(update_df,
                            progress_bar=progress_bar,
                            progress_label=progress_label,
                            o_text=o_text,
                            o_score=o_score_range, 
                            s_text=s_text,
                            s_score=s_score_range, 
                            r_text=r_text,
                            r_score=r_score_range,
                            interdisciplinary_comment=interdisciplinary_comment,
                            my_comment=my_comment,
                            df=fixed(df), index=fixed(index),
                            write_df=fixed(write_df))

    index_select = widgets.Dropdown(options=df.index, value=index)
    interact(update_index, index=index_select, df=fixed(df), write_df=fixed(write_df))
    print("Saved")


