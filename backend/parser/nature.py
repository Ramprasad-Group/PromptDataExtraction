from .tabular import TableParser
from .document import HTMLDocumentParser


class NatureParser(HTMLDocumentParser):
    """ HTML document parser for Nature papers.
    Parameters:
        filepath (string): Path to the Nature HTML paper.
    !!! note
        Nature does not include the full tables. Additional downloads
        might be necessary.
    """
    def __init__(self, filepath) -> None:
        super().__init__('nature', filepath)
        self.tableParser = _natureTableParser

        # Meta
        self.title_xpath = '//h1'
        self.journal_xpath = '//header/p[@class="c-article-info-details"]//i'
        self.date_xpath = '//header//time'
        self.abstract_xpath = '//section[@data-title="Abstract"]//p'
        self.body_xpath = '//div[@class="c-article-body"]'

    def _full_table_links(self, tree) -> list:
        # Find all a elements with an href attribute containing '/tables/'
        # Works for springer and nature.
        a_elements = tree.xpath('//a[contains(@href, "/tables/")]')
        return a_elements


class _natureTableParser(TableParser):
    def __init__(self) -> None:
        super().__init__()

    def parse(self, table_element):
        super().parse(table_element)

        # XPath of caption relative to the table element
        self.caption_rxpath = './/../../figcaption'
        captions = table_element.xpath(self.caption_rxpath)

        if len(captions) > 0:
            self.parse_caption_label(captions[0], label=None)
