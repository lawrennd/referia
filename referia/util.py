"""Utility functions for helping, e.g. to create the relevant yaml files quickly."""

def camel_capitalize(text):
    if text == text.upper():
        return text
    else:
        return text.capitalize()
    

def to_camel_case(text):
    text = text.replace("/", " or ")
    text = text.replace("@", " at ")
    non_alpha_chars = [ch for ch in set(list(text)) if not ch.isalnum()]
    for ch in non_alpha_chars:
        text = text.replace(ch, " ")
    s = text.split()
    if len(text) == 0:
        return A
    if s[0] == s[0].upper():
        start = s[0]
    else:
        start = s[0].lower()
        
    return start + ''.join(camel_capitalize(i) for i in s[1:])


def draft_combinator(fieldname, columns):
    print("- field: {fieldname}".format(fieldname=fieldname))
    print("  display: \"")
    for column in columns:
        print("{fieldContent}: {o}{field}{c}\\n".format(field=to_camel_case(column), fieldContent=column, o ="{", c="}"))
    print("\"")
    print("  format:")
    for column in columns:
        print("    {field}: {fieldContent}".format(field=to_camel_case(column), fieldContent=column))
