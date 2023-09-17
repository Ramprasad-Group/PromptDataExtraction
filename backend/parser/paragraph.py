import pylogg
from lxml import etree
from backend.text import normalize

log = pylogg.New('paragraph')

class ParagraphParser(object):
    def __init__(self):
        self.name = None
        self.text = None
        self.body = None

    def _is_reference(self, text : str) -> bool:
        """ Return True if a text looks like a bibliographic reference. """
        if "http" and "doi" in text:
            return True
        
        if ". et al." in text:
            return True

        # If there are a lot of dots and commas, return true.
        dots = text.count(".")
        commas = text.count(",")
        punctuations = dots + commas
        if punctuations / len(text) > 0.1:
            return True
        
        return False
    
    def _clean_text(self, text : str) -> str:
        """ Clean up a text string, return empty if its a reference."""
        if text is None:
            return ""
        if not self._is_reference(text):
            text = normalize.normText(text)
        else:
            text = ""
        return text

    def _innerText(self, element):
        """ Recursively loop through the child elements to get the complete
        inner text and handle special tags such as sup, sub etc.
        """
        text = " "
        tail = " "
        cleanedtext = self._clean_text(element.text)
        cleanedtail = self._clean_text(element.tail)

        if cleanedtext:
            localname = etree.QName(element).localname
            if localname == 'sup':
                text += "^{" + cleanedtext + "} "
            elif localname == 'sub':
                text += "_{" + cleanedtext + "} "
            elif localname == 'inf':
                text += "_{" + cleanedtext + "} "
            else:
                text += cleanedtext + " "

        childtexts = []
        for child in element:
            childtexts.append(self._innerText(child))

        if cleanedtail:
            tail = cleanedtail

        fulltext = text + " ".join(childtexts) + tail
        return normalize.normText(fulltext)

    def parse(self, paragraph_element):
        """ Parse the inner text of a paragraph element. """

        self.body = paragraph_element
        self.text = self._innerText(paragraph_element)

        # print("InnerText:", self.text)
        # self.save("test.html")
        # input("\nPress enter ...")

    def is_valid(self) -> bool:
        """ Return true if the parsed paragraph is valid.
        """
        criteria = [
            "." in self.text,
            len(self.text) > 10,
            len(self.text.split()) > 5,
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
