import re
from lxml import etree
from unidecode import unidecode

from backend.types import Property


RE_NUMBER = r'[+-]?\d+[.]?\d*(?:\s?±\s?\d+[.]?\d*)?(?:x10\^{[-]?\d*})?'
RE_EXP = r'10\^{[-]?\d*}'
RE_EXP_UNIT = r'([a-zA-Z]+\^{[-]?\d*})'
VALUE_RELATIONS = ['<', '>', '~', '=', 'and', '≈', 'to', '-']


def to_numeric(value : str) -> float:
    """ Convert a string to float by taking scientific notations into
        account.
        Returns the float representation.

        value :
            The string to convert to float.
    """
    if '^{' in value and '}' in value and 'x' in value:
        mantissa, exponent = value.split('x')[0].strip(), value.split('x')[1].strip().replace('10^{', '').replace('}', '')
        numeric_value = float(mantissa)*10**(float(exponent))
        return numeric_value
    elif '^{' in value and '}' in value and 'x' not in value:
        exponent = value.strip().replace('10^{', '').replace('}', '')
        numeric_value = 10**(float(exponent))
        return numeric_value
    else:
        return float(value)


def cleanup_property(prop : Property) -> Property:
    """ Cleanup the value and unit text of a property by normalizing hyphens,
        scientific notations, stadard deviations etc.
        Return the cleaned Property.
    """
    value = str(prop.value)

    # Property value needs some pre-processing to replace exponents
    # in units that could match a number.
    # Might also have to split on - to capture the negative sign.
    value = re.sub(r'(\d)-(\d)', '\\1 - \\2', value)
    value = re.sub(r'(\d) (\d)', '\\1\\2', value)
    value = re.sub(r'(\d) x (\d)', '\\1x\\2', value)

    units_to_replace = re.findall(RE_EXP_UNIT, value)
    units_dict = dict()

    for i, unit in enumerate(units_to_replace):
        units_dict[f'AAA{chr(i+64)}'] = unit
        value = value.replace(unit, f'AAA{chr(i+64)}')

    numeric_values = re.findall(RE_NUMBER, value)
    # print(numeric_values)

    for value in numeric_values:
        if '±' in value:
            values = value.split('±')
            prop.value = to_numeric(values[0].strip())
            prop.error = to_numeric(values[-1].strip())
            break
    else:
        if numeric_values:
            prop.value = sum([to_numeric(num) for num in numeric_values])/(len(numeric_values))
        else:
            prop.value = None
    
    # Deal with cases like 10^{7} not covered by our regular expressions..
    # Hack solution, find a way to integrate this with our regular expression
    if '10^{' in value and not any(['10^{' in value for value in numeric_values]):
        numeric_values = re.findall(RE_EXP, value)
        if numeric_values:
            prop.value = sum([to_numeric(num) for num in numeric_values])/(len(numeric_values))
        else:
            prop.value = None

    
    prop.numeric_value_avg = len(numeric_values) > 1
    leftover_str = value
    for value in numeric_values:
        leftover_str = leftover_str.replace(value, '')

    # Replace units back
    prop.relation = ''

    for str_item in VALUE_RELATIONS:
        if str_item in leftover_str:
            prop.relation = prop.relation + str_item
            leftover_str = leftover_str.replace(str_item, '')

    for key, value in units_dict.items():
        leftover_str = leftover_str.replace(key, value)

    prop.unit = leftover_str.strip()
    # unit_conversion(prop)
    return prop


def cleanup_parentheses(text : str) -> str:
    """ Normalize and clean up parentheses and brackets by removing
        spaces and extras.

        text :
            The text to clean up.
    """
    text = text.replace(' )', ')')
    text = text.replace(' }', '}')
    text = text.replace(' - ', '-')
    text = text.replace(' ( ', '(')
    text = text.replace('{ ', '{')
    text = text.replace(' _ ', '_')
    text = text.replace(' , ', ',')
    text = text.replace(' / ', '/')
    text = text.replace('( ', '(')
    text = text.replace("' ", "'")
    text = text.replace(" '", "'")
    text = text.replace('" ', '"')
    text = text.replace(' "', '"')
    text = text.replace('[ ', '[')
    text = text.replace(' ]', ']')
    text = text.replace(' : ', ':')
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
                raise ValueError("Character:", ntext[-20:], c)
            
    # Remove multiple spaces.
    ntext = re.sub(r'\s+', ' ', ntext).strip()

    # Cleanup some extra spaces.
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
