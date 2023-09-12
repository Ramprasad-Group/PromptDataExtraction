from .tabular import TableParser
from .document import HTMLDocumentParser


class WileyParser(HTMLDocumentParser):
    def __init__(self, filepath) -> None:
        super().__init__('wiley', filepath)
        self.tableParser = _wileyTableParser

        # Meta
        self.abstract_xpath = '//div[@class="abstract-group"]'
        self.date_xpath     = '//span[@class="epub-date"]'
        self.body_xpath     = '//section[@class="article-section article-section__full"]'
        self.journal_xpath  = '//div[@class="journal-banner-text"]'

    def parse_meta(self):
        super().parse_meta()

        if self.journal.strip() == "":
            self.journal_xpath = '//h1'
            self.journal = self.xpath_to_string(self.journal_xpath)
            self.title_xpath = '//h2'
            self.title = self.xpath_to_string(self.title_xpath)

        if self.abstract.strip() == "":
            self.abstract_xpath = '//section[@class="article-section article-section__abstract"]//p'
            self.abstract = self.xpath_to_string(self.abstract_xpath)


class _wileyTableParser(TableParser):
    """ Wiley adds one extra table which contains SI info. """
    def __init__(self) -> None:
        super().__init__()

    def parse(self, table_element):
        super().parse(table_element)

        # XPath of caption relative to the table element
        self.caption_rxpath = './/../../header'
        captions = table_element.xpath(self.caption_rxpath)

        if len(captions) > 0:
            self.parse_caption_label(captions[0], label=None)
