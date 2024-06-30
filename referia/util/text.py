#import spacy

import json
import tempfile
import os
import random
import string
import warnings

from wordcloud import WordCloud, STOPWORDS

import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from string import punctuation
from heapq import nlargest

from ..exceptions import ComputeError
from ..assess import data

nlp = spacy.load("en_core_web_sm")

# -*- coding: utf-8 -*-
import re
alphabets= "([A-Za-z])"
prefixes = "(Mr|St|Mrs|Ms|Dr)[.]"
suffixes = "(Inc|Ltd|Jr|Sr|Co)"
starters = "(Mr|Mrs|Ms|Dr|Prof|Capt|Cpt|Lt|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
websites = "[.](com|net|org|io|gov|edu|me)"
digits = "([0-9])"
multiple_dots = r'\.{2,}'
# from https://stackoverflow.com/questions/4576077/how-can-i-split-a-text-into-sentences

def split_into_sentences(text: str) -> list[str]:
    """
    Split the text into sentences.

    If the text contains substrings "<prd>" or "<stop>", they would lead 
    to incorrect splitting because they are used as markers for splitting.

    :param text: text to be split into sentences
    :type text: str

    :return: list of sentences
    :rtype: list[str]
    """
    text = " " + text + "  "
    text = text.replace("\n"," ")
    text = re.sub(prefixes,"\\1<prd>",text)
    text = re.sub(websites,"<prd>\\1",text)
    text = re.sub(digits + "[.]" + digits,"\\1<prd>\\2",text)
    text = re.sub(multiple_dots, lambda match: "<prd>" * len(match.group(0)) + "<stop>", text)
    if "Ph.D" in text: text = text.replace("Ph.D.","Ph<prd>D<prd>")
    text = re.sub("\s" + alphabets + "[.] "," \\1<prd> ",text)
    text = re.sub(acronyms+" "+starters,"\\1<stop> \\2",text)
    text = re.sub(alphabets + "[.]" + alphabets + "[.]" + alphabets + "[.]","\\1<prd>\\2<prd>\\3<prd>",text)
    text = re.sub(alphabets + "[.]" + alphabets + "[.]","\\1<prd>\\2<prd>",text)
    text = re.sub(" "+suffixes+"[.] "+starters," \\1<stop> \\2",text)
    text = re.sub(" "+suffixes+"[.]"," \\1<prd>",text)
    text = re.sub(" " + alphabets + "[.]"," \\1<prd>",text)
    if "”" in text: text = text.replace(".”","”.")
    if "\"" in text: text = text.replace(".\"","\".")
    if "\\\"" in text: text = text.replace(".\\\"","\\\".")
    if "!" in text: text = text.replace("!\"","\"!")
    if "?" in text: text = text.replace("?\"","\"?")
    text = text.replace(".",".<stop>")
    text = text.replace("?","?<stop>")
    text = text.replace("!","!<stop>")
    text = text.replace("<prd>",".")
    sentences = text.split("<stop>")
    sentences = [s.strip() for s in sentences]
    if sentences and not sentences[-1]: sentences = sentences[:-1]
    return sentences


def render_liquid(data, template, **kwargs):
    """
    Wrapper to liquid renderer.

    :param data: The data to be rendered.
    :type data: dict
    :param template: The template to be rendered.
    :type template: str
    :return: The rendered template.
    :rtype: str
    """
    return data.liquid_to_value(template)
        

def comment_list(text):
    """
    Extract comments from a text string.

    :param text: The text to be extracted from.
    :type text: str
    :return: The comments.
    :rtype: tuple
    """
    pattern = re.compile(r'''
    \[([^\[]*?)\]\{\.comment-start                     # comment-start tag
    \s+id="(\d+)"                           # id
    \s+author="(.*?)"                       # author
    \s+date="(.*?)"\}                       # date
    (.*?)                                   # content between
    \[\]\{\.comment-end\s+id="\2"\}       # paired comment-end tag with the same id
    ''', re.DOTALL | re.VERBOSE)
    matches = pattern.finditer(text)

    starts = []
    finishes = []
    comments = []
    comment_ids = []
    authors = []
    dates = []
    highlight_texts = [] 
    for match in matches:
        #initial_content, _, comment_id, author, date, content_after = match[:6]
        start, finish = match.span()
        comment, comment_id, author, date, highlight_text = match.groups()
        starts.append(start)
        finishes.append(finish)
        comments.append(comment)
        comment_ids.append(comment_id)
        authors.append(author)
        dates.append(date)
        highlight_texts.append(highlight_text)

    return comments, comment_ids, authors, dates, starts, finishes, highlight_texts
        

def word_count(text):
    """
    Count the number of words in a text string using SpaCy, excluding punctuation.

    :param text: The text to be counted.
    :type text: str
    :return: The number of words.
    :rtype: int
    """
    doc = nlp(text)
    words = [token.text for token in doc if not token.is_punct and not token.is_space]
    return len(words)

def word_cloud(text, filename, **kwargs):
    """
    Create a word cloud of the given text.

    :param text: The text to be used.
    :type text: str
    :param filename: The filename to be used.
    :type filename: str
    :return: The word cloud.
    :rtype: WordCloud
    """
    stopwords = set(STOPWORDS)
    wordcloud = WordCloud(width=800, height=800,
                          background_color ='white',
                          stopwords = stopwords,
                          min_font_size = 10).generate(comment_words)
    return wordcloud
    
    
def paragraph_split(text, sep):
    """
    Split a text string into paragraphs.

    :param text: The text to be split.
    :type text: str
    :param sep: The separator to be used.
    :type sep: str
    :return: The split text.
    :rtype: list
    """
    return text.split(sep=sep)

def sentence_split(text):
    """
    Split a text string into sentences using SpaCy.

    :param text: The text to be split.
    :type text: str
    :return: The split text.
    :rtype: list of str
    """
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents]

# Other SpaCy-related functions can be added here

def list_lengths(entries):
    """
    Return the lengths of a list of entries.

    :param entries: The list of entries.
    :type entries: list
    :return: The lengths of the entries.
    :rtype: list
    """
    
    return [len(entry) for entry in entries]


def named_entities(text, ent_type="PERSON"):
    """
    Extract named entities from a text string.

    :param text: The text to be extracted from. Can be "PERSON", "ORG", "GPE", "LOC", "PRODUCT", "EVENT", "WORK_OF_ART", "LANGUAGE", "DATE", "TIME", "PERCENT", "MONEY", "QUANTITY", "ORDINAL", "CARDINAL".
    :type text: str
    :return: The named entities.
    :rtype: list
    """
    
    spacy_parser = nlp(text)
    return [entity.text for entity in spacy_parser.ents if entity.label_==ent_type]


    
def text_summarizer(text, fraction=0.1):
    """
    Summarize a text string.

    :param text: The text to be summarized.
    :type text: str
    :return: The summary.
    :rtype: str
    """
    # based on https://www.kaggle.com/code/itsmohammadshahid/nlp-text-summarizer-using-spacy
    
    # pass the text into the nlp function
    doc = nlp(text)
    
    ## The score of each word is kept in a frequency table
    tokens=[token.text for token in doc]
    freq_of_word=dict()
    
    # Text cleaning and vectorization 
    for word in doc:
        if word.text.lower() not in list(STOP_WORDS):
            if word.text.lower() not in punctuation:
                if word.text not in freq_of_word.keys():
                    freq_of_word[word.text] = 1
                else:
                    freq_of_word[word.text] += 1
                    
    # Maximum frequency of word
    max_freq=max(freq_of_word.values())
    
    # Normalization of word frequency
    for word in freq_of_word.keys():
        freq_of_word[word]=freq_of_word[word]/max_freq
        
    # In this part, each sentence is weighed based on how often it contains the token.
    sent_tokens= [sent for sent in doc.sents]
    sent_scores = dict()
    for sent in sent_tokens:
        for word in sent:
            if word.text.lower() in freq_of_word.keys():
                if sent not in sent_scores.keys():                            
                    sent_scores[sent]=freq_of_word[word.text.lower()]
                else:
                    sent_scores[sent]+=freq_of_word[word.text.lower()]
    
    
    len_tokens=int(len(sent_tokens)*fraction)
    
    # Summary for the sentences with maximum score. Here, each sentence in the list is of spacy.span type
    summary = nlargest(n = len_tokens, iterable = sent_scores,key=sent_scores.get)
    
    # Prepare for final summary
    final_summary=[word.text for word in summary]
    
    #convert to a string
    summary=" ".join(final_summary)
    
    # Return final summary
    return summary

def pdf_extract_comments(filename, directory="", start_page=1, comment_types=["Highlight"], number=None):
    """
    Extract comments from a pdf file.

    :param filename: The filename of the pdf file.
    :type filename: str
    :param directory: The directory of the pdf file.
    :type directory: str
    :param start_page: The starting page.
    :type start_page: int
    :param comment_types: The comment types to be extracted.
    :type comment_types: list
    :param number: The number of the comment to be extracted.
    :type number: int
    :return: The comments.
    :rtype: str
    """
    
    if type(comment_types) is not list:
        comment_types = [comment_types]
    directory = os.path.expandvars(directory)
    full_filename = os.path.join(directory, filename)
    
    if os.path.exists(full_filename):
        tmpdirectory = tempfile.gettempdir()
        tmpname = ''.join(random.choices(string.digits+string.ascii_letters, k=8))
        destfile = "_" + tmpname + ".json"
        destname = os.path.join(tmpdirectory, destfile)
        syscmd = f"pdfannots \"{full_filename}\" -o \"{destname}\" -f json"
        #self._log.debug(f"Running system command: {syscmd}")
        try:
            os.system(syscmd)
        except OSError as err:
            errmsg = f"OSError while running {syscmd} is {err}"
            raise ComputeError(errmsg)
        
        with open(destname, "r") as f:
            data = json.load(f)
        val = ""
        if number is not None:
            data=[data[number]]
        for entry in data:
            if entry["type"] == "FreeText":
                if entry["type"] in comment_types:
                    page = entry["page"] + start_page - 1
                    contents = entry["contents"]
                    val += f"{contents}\n\n"
        for entry in data:
            if entry["type"] == "Highlight":
                if entry["type"] in comment_types:
                    val += f"* "
                    if "page" in entry:
                        page = entry["page"] + start_page - 1
                        val += f"Page {page}:\n\n"
                    if "text" in entry:
                        text = entry["text"]
                        val += f"> {text}\n\n"
                    if "contents" in entry:
                        contents = entry["contents"]
                        val += f"{contents}\n\n"                    
        return val

    else:
        warnings.warn(f"File: {full_filename} is missing in pdf_extract_comments.")
        return ""

