# Fake data ideas initially from https://stackoverflow.com/questions/45574191/using-python-faker-generate-different-data-for-5000-rows
import mimesis as mi
import pandas as pd
import random

person = mi.Person('en')
addess = mi.Address()
datetime = mi.Datetime()
text = mi.Text('en')

def row():
    full_name = person.full_name(gender=mi.enums.Gender.FEMALE)
    name = person.name()
    date_time = datetime.datetime()
    output = {
        "full_name": full_name,
        "address": addess.address(),
        "name": name,
        "email": person.email(),
        "city": addess.city(),
        "state": addess.state(),
        #"date_time": date_time,
        "content": text.text(quantity=30),
        "tagline": text.text(quantity=3),
        "randomdata": random.randint(1000,2000),
    }
    return output

def rows(num_rows):
    return [row() for x in range(num_rows)]

def row_allocation_additional_scores_series(num_ruows):
    given_name = person.first_name()
    family_name = person.surname()
    date1  = datetime.datetime()
    date2 = datetime.datetime()
    if date1 > date2:
        updated = date1
        timestamp = date2
    else:
        updated = date2
        timestamp = date1
    allocation = {
        "family": family_name,
        "given": given_name,
        "timestamp": timestamp,
        "updated": updated,
        }
    allocation["index"] = allocation["family"] + "_" + allocation["given"]
    additional = {
        "index": allocation["index"],
        "address": addess.address(),
        "email": person.email(),
        "city": addess.city(),
        "state": addess.state(),
    }
    scores = {
        "index" : allocation["index"],
        "content": text.text(quantity=30),
        "tagline": text.text(quantity=3),
        "randomdata": random.randint(1000,2000),
    }

    sceries = {
        "index" : allocation["index"],
        "content": text.text(quantity=30),
        "tagline": text.text(quantity=3),
        "randomdata": random.randint(1000,2000),
    }
    
def DataFrame(num_rows):
    return pd.DataFrame(rows(num_rows))

