import re
from .document import XMLDocumentParser


class ACSParser(XMLDocumentParser):
    """
    XML document parser for ACS papers.
    
    """
    def __init__(self, filepath) -> None:
        super().__init__('acs', filepath)

        # ACS XML specific configs
        self.table_xpath = '//*[local-name()="table-wrap"]'
        self.title_xpath = '//*[local-name()="article-title"]'
        self.date_xpath = '//*[local-name()="pub-date" and @pub-type="ppub"]'
        self.journal_xpath = '//*[local-name()="journal-title"]'

    def parse_meta(self):
        super().parse_meta()

        # If date not found
        if self.date.strip() == "":
            self.date_xpath = '//*[local-name()="pub-date" and @date-type="pub"]'
            self.date = self.xpath_to_string(self.date_xpath)

    def parse_tables(self):
        # Table and figure reference numbers are not in inner texts.
        # Manually parse them from xref tags and add them add inner texts.

        pattern = re.compile(r"(\d+)")

        elems = self._tree.xpath('//*[local-name()="xref"]')
        for elem in elems:
            rid = elem.get("rid")

            # rid is an element ID
            dest_label = self._tree.find('//*[@id="{}"]/label'.format(rid))

            # extract the digit
            match = pattern.findall(rid)

            if dest_label is not None:
                par = dest_label.getparent()
                if par.tag.lower().startswith('table'):
                    elem.text = " Table " + dest_label.text
            elif len(match) == 1:
                if rid.startswith("tbl"):
                    elem.text = " Table " + match[0]
                elif rid.startswith("fig"):
                    elem.text = " Figure " + match[0]
    
        # Debugging purposes
        # self._tree.write("test.xml")

        # hand over to the parent parser
        return super().parse_tables()

    def parse_paragraphs(self):
        self.para_xpath = '//*[local-name()="p"]'
        return super().parse_paragraphs()
