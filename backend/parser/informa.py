from .tabular import TableParser
from .document import HTMLDocumentParser


class InformaParser(HTMLDocumentParser):
    """ Informa sometimes wraps lists inside tables!! 
        In some cases, both table tags and link to full tables exist.
    """
    def __init__(self, filepath) -> None:
        super().__init__('informa_uk', filepath)
        self.tableParser = _informaTableParser

        # Meta
        self.title_xpath = '(//h1)[3]'
        self.journal_xpath = '(//h1)[1]'
        self.date_xpath = '(//div[@class="container-fluid"])[1]//div[starts-with(text(), "Published")]'
        self.abstract_xpath = '//div[contains(@class, "abstractSection")]//p'
        self.body_xpath = '//div[@class="hlFld-Fulltext"]'

    def _full_table_links(self, tree) -> list:
        a_elements = []
        return a_elements

    def parse_meta(self):
        super().parse_meta()

        if self.title.strip() == "":
            self.title_xpath = '(//h1)[2]'
            self.title = self.xpath_to_string(self.title_xpath)
            self.abstract_xpath = '//div[contains(@class, "abstractSection")]//p[2]'
            self.abstract = self.xpath_to_string(self.abstract_xpath)

        if self.abstract.strip() == "":
            self.abstract_xpath = '//div[@class="abstractSection abstractInFull"]'
            self.abstract = self.xpath_to_string(self.abstract_xpath)

        if self.title.strip() == self.journal.strip():
            self.journal_xpath = '//span[@class="journal-heading"]'
            self.journal = self.xpath_to_string(self.journal_xpath)


        if self.date.strip() == "":
            self.date_xpath = '//div[starts-with(text(), "Published")]'
            self.date = self.xpath_to_string(self.date_xpath)
    
    def parse_paragraphs(self):
        self.para_xpaths = ['//*[local-name()="p"]']
        return super().parse_paragraphs()


class _informaTableParser(TableParser):
    def __init__(self) -> None:
        super().__init__()

    def parse(self, table_element):
        super().parse(table_element)

        # XPath of caption relative to the table element
        caption_rxpath = './/../div[@class="caption"]'
        captions = table_element.xpath(caption_rxpath)

        if len(captions) > 0:
            self.parse_caption_label(captions[0], label=None)
