import re
import html
import unidecode
from lxml import etree
from textacy import preprocessing

def normalize_parentheses(text: str) -> str:
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


def asciiText(unicode_text: str):
    """ Convert unicode text to ASCII. """
    raise RuntimeError("Please use TextNormalizer.")


def normText(text: str):
    """ Normalize a string to remove extra spaces and special characters etc."""
    norm = TextNormalizer()
    return norm.norm_chars(text)


def innerText(elem):
    """ Return the innerText of a XML element. Normalize using normText. """
    value = etree.tostring(elem, method="text", encoding="unicode")
    value = normText(value)
    return value


class TextNormalizer:
    """
        Remove formatting symbols.
        Rormalize degree symbols, deg. C, abbreviations with dots.

        Replaces symbols starting from & with unicode equivalents.
        Figure, reference and table normalization.

        Unidecode

        Remove accents, replace all unicode characters with ASCII equivalents.
        Problem greek characters
        solution: normalize string characters except greek char and limited
        exception list.

        Use HTMLParser Unescape?
        Converts HTML entities to unicode entities, (should be done before
        applying unidecode).

        What ascii characters other than greek characters would we like to keep?

        CDE

        Normalize tildes, slashes, control characters and ellipsis,
        rest taken care of Chemical entity normalization

        Use stuff from our pre-processing code
        Remove [] and [,] which are left over from processing references.

        Optionally replace numbers, can use textacy method for this,
        Table numbers
        Filter fractions
        Filter multiple spaces in between and trailing whitespaces
    """

    def __init__(self):
        self.TILDES = {
            '~',  # \u007e Tilde
            '˜',  # \u02dc Small tilde
            '⁓',  # \u2053 Swung dash
            '∼',  # \u223c Tilde operator
            '∽',  # \u223d Reversed tilde
            '∿',  # \u223f Sine wave
            '〜',  # \u301c Wave dash
            '～',  # \uff5e Full-width tilde
        }
        self.SLASHES = {
            '/',  # \u002f Solidus
            '⁄',  # \u2044 Fraction slash
            '∕',  # \u2215 Division slash
        }
        self.CONTROLS = {
            '\u0001', '\u0002', '\u0003', '\u0004', '\u0005', '\u0006',
            '\u0007', '\u0008', '\u000e', '\u000f', '\u0011', '\u0012',
            '\u0013', '\u0014', '\u0015', '\u0016', '\u0017', '\u0018',
            '\u0019', '\u001a', '\u001b',
        }
        self.replace_char_list = ['[]', '[,]', '()', '( )', '[ ]', ' - ']
        self.remove_dot_list = [
            'Dr.', 'Mr.', ',Mrs.', 'et al.', 'cf.', 'viz.', 'etc.', 'Corp.',
            'Inc.', 'spp.', 'Co.', 'Ltd.', 'eg.', 'ex.',
        ]
        self.remove_all_dot_list = ['A.R.', 'A. R.', 'i.e.', 'e.g.']

        # unicode character codes
        self.degrees = [186, 730, 778, 8304, 8728,
                        9702, 9675]  
        self.to_remove = [775, 8224, 8234, 8855, 8482, 9839]

        self.formatting = [i for i in range(
            8288, 8298)] + [i for i in range(8299, 8304)] + [i for i in range(8232, 8239)]

        self.re_copyright = re.compile(
            r'© \d{4} .+', flags=re.UNICODE | re.IGNORECASE)

        self.re_consecutive_spaces = re.compile(
            r'\s+', flags=re.UNICODE | re.IGNORECASE)

    def normalize(self, text, unidec=True, chem=True, spaces=True, fig_ref=True,
                  numbers=False, lower_case=False):
        # Use a bunch of textacy functions to pre-process.
        text = html.unescape(text)
        text = preprocessing.replace.emails(text)
        text = preprocessing.replace.urls(text)

        for char_seq in self.replace_char_list:
            text = text.replace(char_seq, '')

        # Remove some boiler plate symbols
        re_str = ''.join([chr(c) for c in self.to_remove])
        re_str = '[' + re_str + ']'
        text = re.sub(re_str, '', text)

        # Replaces empty brackets that are left over from removing references after parsing the HTML
        for chr_seq in self.remove_dot_list:
            text = text.replace(chr_seq, chr_seq[:-1])

        # Fixes issues where the superscript and variable might have a space between them
        text = re.sub(r'\s+(\^{\w*})', '\\1', text)
        # Fix the cases where NMR related terms get clubbed with previous terms
        text = re.sub(r'(\^\{1\}H)', ' \\1', text)
        # TODO: There must be other terms which get similarly clubbed
        text = re.sub(r'(\^\{13\}C)', ' \\1', text)
        text = re.sub(r'(\^\{7\}Li)', ' \\1', text)
        # Fixes issues where the subscript and variable might have a space between them
        text = re.sub(r'\s+(_{\w*})', '\\1', text)
        # Fixes issues where the end bracket and variable in superscript might have a space between them
        text = re.sub(r'(\^{\w*)\s+}', '\\1}', text)
        # Fixes issues where the end bracket and variable in subscript might have a space between them
        text = re.sub(r'(_{\w*\s+)}', '\\1}', text)

        # Removes dots as they may cause problems in recognizing sentences
        for chr_seq in self.remove_all_dot_list:
            chr_dotless = chr_seq.replace('.', '')
            text = text.replace(chr_seq, chr_dotless)

        # TextCleanup inspired code
        # Degree normalization
        re_str = '[' + ''.join([chr(c) for c in self.degrees]) + ']'
        text = re.sub(re_str, chr(176), text)
        text = text.replace('° C', '°C')
        text = text.replace('°C', ' °C')

        # Removes copyright notices expected to be at the end of abstracts
        text = self.re_copyright.sub('', text)

        # Figure and references
        if fig_ref:
            text = re.sub(r'Fig.\s*([0-9]+)', 'Figure \\1', text)
            text = re.sub(r'[Rr]ef.\s*([0-9]+)', 'reference \\1', text)
            text = re.sub(r'\sal\.\s*[0-9\s]+', ' al ', text)

        # Normalizing spaces
        if spaces:
            text = text.replace('\u000b', ' ').replace(
                '\u000c', ' ').replace(u'\u0085', ' ')
            text = text.replace('\u2028', '\n').replace(
                '\u2029', '\n').replace('\r\n', '\n').replace('\r', '\n')
            text = text.replace('\n', ' ')

            text = re.sub(r'\s+,', ',', text)
            # remove coma in thousands
            text = re.sub(r'([1-9]),([0-9]{3})', '\\1\\2', text)
            # Put a space around = to sign everywhere
            text = re.sub(r'(\w+)=(\d+)', '\\1 = \\2', text)
            text = re.sub(r'\(\s+', '(', text)
            text = text.replace('%', ' %')  # Normalize % character
            # Multiple spaces before a bracket
            text = text.replace('\s+)', ')')
            text = re.sub(r'(\d+),([A-Za-z])', '\\1, \\2', text)

        if chem:
            text = self.chem_normalizer(text)

        if unidec:
            text = self.unidecode_normalize_string(text)

        else:
            text = preprocessing.normalize.unicode(text)
            text = preprocessing.normalize.hyphenated_words(text)
            text = preprocessing.normalize.quotation_marks(text)
            text = preprocessing.normalize.whitespace(text)
            text = preprocessing.remove.remove_accents(text)
            text = text.replace('…', '...').replace(' . . . ', ' ... ')

            re_str = ''.join([chr(c) for c in self.formatting])
            re_str = '[' + re_str + ']'
            text = re.sub(re_str, '', text)

            for tilde in self.TILDES:
                text = text.replace(tilde, '~')

            for slash in self.SLASHES:
                text = text.replace(slash, '/')

            for control in self.CONTROLS:
                text = text.replace(control, '')

        if numbers:
            text = preprocessing.replace.replace_numbers(text)
            regex_fraction = '[-]?\d+[/]\d+'
            text = re.sub(regex_fraction, ' _FRAC_ ', text)

        if lower_case:
            text = text.lower()

        text = self.re_consecutive_spaces.sub(' ', text).strip()

        return text

    def unidecode_normalize_string(self, string : str) -> str:
        ret_string = ''
        for char in string:
            if re.match(u'[Α-Ωα-ωÅ°±≈⋯∞∆ϵ⋅≫≡≅≃∙≠]', char) is not None:
                ret_string += str(char)
            else:
                ret_string += str(
                    unidecode.unidecode_expect_nonascii(str(char)))

        return ret_string


    def chem_normalizer(self, text : str) -> str:
        """Normalizes certain very common chemical name variations"""
        # Can probably add to this list of rules.
        text = re.sub(r'sulph', r'sulf', text, flags=re.I)
        text = re.sub(r'aluminum', r'aluminium', text, flags=re.I)
        text = re.sub(r'cesium', r'caesium', text, flags=re.I)

        return text

    def norm_chars(self, text : str) -> str:
        """ Manually normalize special characters and spaces. """
        ntext = ""
        i = 0
        while i < len(text):
            # current char
            c = text[i]
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
            elif c == 'Î' and self._text_char(text, i) == '¼':
                ntext += "\\mu "
                i += 1
            elif c == 'Ï' and self._text_char(text, i) == 'â':
                ntext += "pi-"
                i += 1
            elif c == 'Î' and self._text_char(text, i) == '±':
                ntext += "\\alpha"
                i += 1
            elif c == 'Ï' and self._text_char(text, i) == 'â':
                ntext += "pi-"
                i += 1
            elif c == 'Ï' and self._text_char(text, i) == 'â':
                ntext += "pi-"
                i += 1
            elif c == 'Ï' and self._text_char(text, i) == 'â':
                ntext += "pi-"
                i += 1
            elif c == 'Ï' and self._text_char(text, i) == 'â':
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
            elif c == 'ï' and self._text_char(text, i) == '£' \
                    and self._text_char(text, i+1) == '½':
                ntext += "---"
                i += 2
            elif c == 'ö':
                ntext += "o"
            elif c == 'ü':
                ntext += "u"
            # elif c == 'ö':
            #     ntext += "o"
            # elif c == 'ö':
            #     ntext += "o"
            # elif c == 'ö':
            #     ntext += "o"
            # elif c == 'ö':
            #     ntext += "o"
            # elif c == 'ö':
            #     ntext += "o"
            # elif c == 'ö':
            #     ntext += "o"
            # elif c == 'ö':
            #     ntext += "o"
            # elif c == 'ö':
            #     ntext += "o"
            # elif c == 'ö':
            #     ntext += "o"
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

    def _text_char(self, text: str, position: int = 1) -> str:
        try:
            return text[position]
        except IndexError:
            return ''
