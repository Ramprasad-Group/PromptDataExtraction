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
    """ Cleanup the value and unit text of a property.
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



def asciiText(unicode_text : str):
    """ Convert unicode text to ASCII. """
    return unidecode(unicode_text)

def normText(text : str):
    """ Normalize a string to remove extra spaces etc. """
    return re.sub(r'\s+', ' ', text).strip()

def innerText(elem):
    """ Return the innerText of a XML element. Normalize using normText. """
    value = etree.tostring(elem, method="text", encoding="unicode")
    value = normText(value)
    return value
