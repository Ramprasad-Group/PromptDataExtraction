import pylogg
from lxml import etree
from backend.text import normalize

log = pylogg.New('paragraph')

class ParagraphParser(object):
    def __init__(self):
        self.name = None
        self.text = None
        self.body = None

    def parse(self, paragraph_element):
        """ Parse the inner text of a paragraph element. """
        self.body = paragraph_element
        self.text = normalize.innerText(paragraph_element)

    def is_valid(self) -> bool:
        """ Return true if the parsed paragraph is valid.
        """
        criteria = [
            "." in self.text,
            len(self.text) > 10
        ]
        return all(criteria)

    def save(self, outfile):
        """ Save the raw HTML of the paragraph body for debugging purposes.
        """
        fp = open(outfile, "w+")
        html = etree.tostring(self.body, encoding="unicode", method='xml')
        fp.write(html)
        fp.write("\n")
        fp.close()
        print("Save OK: ", outfile)
