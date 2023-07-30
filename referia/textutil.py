import nltk
import spacy
from matplotlib import pyplot as plt

nlp = spacy.load("en_core_web_sm")

def word_count(text):
    tokenizer = nltk.RegexpTokenizer(r'\w+')
    wc = len(tokenizer.tokenize(text))
    return wc


def paragraph_split(text, sep):
    return text.split(sep=sep)

def list_lengths(entries):
    return lambda entries: [len(entry) for entry in entries]


def named_entities(text, ent_type="PERSON"):
    spacy_parser = nlp(text)
    return [entity.text for entity in spacy_parser.ents if entity.label_==ent_type]
    #tokens = nltk.word_tokenize(text)
    #pos_tags = nltk.pos_tag(tokens)
    #return nltk.ne_chunk(pos_tags)    

def paragraph_count(paragraphs):
    return [word_count(paragraph) for paragraph in paragraphs]

def bar_plot(values):
    pass

    
