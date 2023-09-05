import pylogg
from lxml import etree
from backend.text import normalize

log = pylogg.New('paragraph')

class ParagraphParser(object):
    def __init__(self):
        self.name = None
        self.text = None
        self.body = None

    def _innerText(self, element):
        text = " "

        if element.text is not None:
            if element.tag == 'sup':
                text += "^{" + normalize.normText(element.text) + "} "
            elif element.tag == 'sub':
                text += "_{" + normalize.normText(element.text) + "} "
            else:
                text += normalize.normText(element.text)

        childtexts = []
        for child in element:
            childtexts.append(self._innerText(child))

        if element.tail is not None:
            tailtext = normalize.normText(element.tail)
        else:
            tailtext = " "

        fulltext = text + " ".join(childtexts) + tailtext
        return fulltext

    def parse(self, paragraph_element):
        """ Parse the inner text of a paragraph element. """

        self.body = paragraph_element

        self.text = self._innerText(paragraph_element)
        self.text = normalize.normText(self.text)

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
