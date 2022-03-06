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
        "address":addess.address(),
        "name":name,
        "email":person.email(),
        "city":addess.city(),
        "state":addess.state(),
        # "date_time": date_time,
        "content":text.text(quantity=30),
        "tagline":text.text(quantity=3),
        "randomdata":random.randint(1000,2000),
    }
    return output

def rows(rows):
    return [row() for x in range(rows)]
