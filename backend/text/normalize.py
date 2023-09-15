import re
from lxml import etree
from unidecode import unidecode

def normalize_parentheses(text : str) -> str:
    """ Normalize and clean up parentheses and brackets by completing pairs.

        text :
            The text to clean up.
    """
    if text.count('}') == text.count('{')-1:
        text = text+'}'
    if text.count(')') == text.count('(')-1:
        # Assumes the missing closing bracket is in the end which is reasonable
        text = text+')'
    elif text.count(')') == text.count('(')+1:
        # Last ) is being removed from the list of tokens which is ok
        text = text[:-1]
    return text


def asciiText(unicode_text : str):
    """ Convert unicode text to ASCII. """
    return unidecode(unicode_text)

def text_char(text : str, position : int = 1) -> str:
    try:
        return text[position]
    except IndexError:
        return ''

def normText(text : str):
    """ Normalize a string to remove extra spaces etc. """
    ntext = ""
    i = 0
    while i < len(text):
        # current char
        c  = text[i]
        i += 1

        if c == 'â':
            ntext += "-"
        elif c == 'Â':
            ntext += ""
        elif c == '\x80':
            ntext += ""
        elif c == '\x85':
            ntext += ""
        elif c == '\x86':
            ntext += ""
        elif c == '\x88':
            ntext += ""
        elif c == '\x89':
            ntext += ""
        elif c == '\x90':
            ntext += ""
        elif c == '\x92':
            ntext += ""
        elif c == '\x93':
            ntext += ""
        elif c == '\x94':
            ntext += ""
        elif c == '\x97':
            ntext += ""
        elif c == '\x98':
            ntext += ""
        elif c == '\x99':
            ntext += ""
        elif c == '\x8d':
            ntext += ""
        elif c == '\x9c':
            ntext += ""
        elif c == '\x9d':
            ntext += ""
        elif c == '\x96':
            ntext += ""
        elif c == '\x8b':
            ntext += ""
        elif c == '\xa0':
            ntext += " "
        elif c == '©':
            ntext += "(c)"
        elif c == '¼':
            ntext += "1/4"
        elif c == 'Ã':
            ntext += ""
        elif c == '®':
            ntext += "(R)"
        elif c == '¶':
            ntext += "\n"
        elif c == 'Ä':
            ntext += ""
        elif c == '²':
            ntext += "^{2}"
        elif c == 'µ':
            ntext += "\\mu"
        elif c == '′':
            ntext += "'"
        elif c == '“':
            ntext += '"'
        elif c == '‐':
            ntext += "-"
        elif c == '–':
            ntext += "-"
        elif c == '°':
            ntext += "°"
        elif c == '±':
            ntext += "+/-"
        elif c == '−':
            ntext += "-"
        elif c == '\uf8ff':
            ntext += "-"
        elif c == '¤':
            ntext += ""
        elif c == '≈':
            ntext += "~"
        elif c == 'α':
            ntext += "\\alpha"
        elif c == '’':
            ntext += "'"
        elif c == 'Î' and text_char(text, i) == '¼':
            ntext += "\\mu "
            i += 1
        elif c == 'Ï' and text_char(text, i) == 'â':
            ntext += "pi-"
            i += 1
        elif c == 'Î' and text_char(text, i) == '±':
            ntext += "\\alpha"
            i += 1
        elif c == 'Ï' and text_char(text, i) == 'â':
            ntext += "pi-"
            i += 1
        elif c == 'Ï' and text_char(text, i) == 'â':
            ntext += "pi-"
            i += 1
        elif c == 'Ï' and text_char(text, i) == 'â':
            ntext += "pi-"
            i += 1
        elif c == 'Ï' and text_char(text, i) == 'â':
            ntext += "pi-"
            i += 1
        elif c == '×':
            ntext += "x"
        elif c == '\uf8fe':
            ntext += "="
        elif c == '\u2005':
            ntext += " "
        elif c == 'β':
            ntext += "\\beta"
        elif c == 'ζ':
            ntext += "\\zeta"
        elif c == 'ï' and text_char(text, i) =='£' \
            and text_char(text, i+1) == '½':
                ntext += "---"
                i += 2
        elif c == 'ö':
            ntext += "o"
        elif c == 'ü':
            ntext += "o"
        elif c == 'ö':
            ntext += "o"
        elif c == 'ö':
            ntext += "o"
        elif c == 'ö':
            ntext += "o"
        elif c == 'ö':
            ntext += "o"
        elif c == 'ö':
            ntext += "o"
        elif c == 'ö':
            ntext += "o"
        elif c == 'ö':
            ntext += "o"
        elif c == 'ö':
            ntext += "o"
        elif c == 'ö':
            ntext += "o"
        else:
            try:
                c = c.encode('utf-8').decode('utf-8')
                ntext += c
            except:
                # If additional special characters are found,
                # add them to the above elif cases.
                print(text[i-50:i+50])
                raise ValueError("Unknown Character:", ntext[-20:], c)
            
    # Add space before (
    ntext = ntext.replace("(", " (")

    # Remove multiple consecutive spaces.
    ntext = re.sub(r'\s+', ' ', ntext).strip()

    # Cleanup some extra spaces.
    ntext = ntext.replace(" isa ", " is a ")
    ntext = ntext.replace("( ", "(")
    ntext = ntext.replace(" )", ")")
    ntext = ntext.replace("- ", "-")
    ntext = ntext.replace(" ^", "^")
    ntext = ntext.replace(" _", "_")
    ntext = ntext.replace("}=", "} =")
    ntext = ntext.replace(" , ", ", ")
    ntext = ntext.replace("^{[}", "[")
    ntext = ntext.replace("^{]}", "]")
    ntext = ntext.replace("-\\x89", "")

    return ntext


def innerText(elem):
    """ Return the innerText of a XML element. Normalize using normText. """
    value = etree.tostring(elem, method="text", encoding="unicode")
    value = normText(value)
    return value
