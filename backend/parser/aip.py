from .tabular import TableParser
from .document import HTMLDocumentParser


class AIPParser(HTMLDocumentParser):
    """ HTML document parser for AIP papers.
    """
    def __init__(self, filepath) -> None:
        super().__init__('aip', filepath)
        self.tableParser = _aipTableParser

        # Meta
        self.title_xpath = '//h1'
        self.journal_xpath = '//div[@class="header-journal-title"]/a'
        self.date_xpath = '//div[contains(@class, "publicationContentEpubDate")]'
        self.abstract_xpath = '//div[contains(@class, "abstractSection")]/div'
        self.body_xpath = '//div[@class="hlFld-Fulltext"]'

    def _full_table_links(self, tree) -> list:
        a_elements = []
        return a_elements
    
    def parse_meta(self):
        super().parse_meta()

        # Check abstract is ok
        if len(self.abstract) <= 12:
            self.abstract_xpath = '//div[@class="hlFld-Abstract"]'
            self.abstract = self.xpath_to_string(self.abstract_xpath)

        # Check pub date is ok
        if len(self.date.strip()) == 0:
            self.date_xpath = '//span[@class="dates"][3]'
            self.date = self.xpath_to_string(self.date_xpath)

        if len(self.date.strip()) == 0:
            self.date_xpath = '//span[@class="dates"][1]'
            self.date = self.xpath_to_string(self.date_xpath)

        self.clean()

    def parse_paragraphs(self):
        self.para_xpath = '//div[@class="NLM_paragraph"]'
        return super().parse_paragraphs()


class _aipTableParser(TableParser):
    def __init__(self) -> None:
        super().__init__()

    def parse(self, table_element):
        super().parse(table_element)

        # XPath of caption relative to the table element
        self.caption_rxpath = './/../../preceding-sibling::div[@class="NLM_table"][1]'
        captions = table_element.xpath(self.caption_rxpath)

        if len(captions) > 0:
            self.parse_caption_label(captions[0], label=None)
