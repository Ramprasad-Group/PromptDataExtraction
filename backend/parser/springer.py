from .tabular import TableParser
from .document import HTMLDocumentParser


class SpringerParser(HTMLDocumentParser):
    """ HTML document parser for Springer papers.
    !!! note
        Springer does not include the full tables. Additional downloads
        might be necessary.
    """
    def __init__(self, filepath) -> None:
        super().__init__('springer', filepath)
        self.tableParser = _springerTableParser

        self.title_xpath = '//header/h1'
        self.journal_xpath = '//header/p[@class="c-article-info-details"]//i'
        self.date_xpath = '//header//time'
        self.abstract_xpath = '//section[@data-title="Abstract"]//p'
        self.body_xpath = '//div[@class="c-article-body"]'

    def _full_table_links(self, tree) -> list:
        # Find all a elements with an href attribute containing '/tables/'
        # Works for springer and nature.
        a_elements = tree.xpath('//a[contains(@href, "/tables/")]')
        return a_elements

    def parse_meta(self):
        super().parse_meta()

        # If not found
        if self.title.strip() == "":
            self.title_xpath = '//h1'
            self.title = self.xpath_to_string(self.title_xpath)

        # If not found
        if self.abstract.strip() == "":
            self.abstract_xpath = '//div[@id="Abs1-content"]//p'
            self.abstract = self.xpath_to_string(self.abstract_xpath)

        if self.abstract.strip() == "":
            self.abstract_xpath = '//section[@class="Abstract"]//p'
            self.abstract = self.xpath_to_string(self.abstract_xpath)

        if self.abstract.strip() == "":
            self.abstract_xpath = '//section[@class="abstract"]//p'
            self.abstract = self.xpath_to_string(self.abstract_xpath)

        if self.abstract.strip() == "":
            self.abstract_xpath = '//div[@class="section--abstract"]//p'
            self.abstract = self.xpath_to_string(self.abstract_xpath)

        if self.date.strip() == "":
            self.date_xpath = '//time'
            self.date = self.xpath_to_string(self.date_xpath)
                
        if self.journal.strip() == "":
            self.journal_xpath = '//a[@data-test="ConfSeriesLink"]'
            self.journal = self.xpath_to_string(self.journal_xpath)
        
        if self.journal.strip() == "":
            self.journal_xpath = '//div[@class="ArticleHeader main-context"]//a'
            self.journal = self.xpath_to_string(self.journal_xpath)
        
        if self.body.strip() == "":
            self.body_xpath = '//div[@id="body"]'
            self.body = self.xpath_to_string(self.body_xpath)

class _springerTableParser(TableParser):
    def __init__(self) -> None:
        super().__init__()

    def parse(self, table_element):
        super().parse(table_element)

        # XPath of caption relative to the table element
        self.caption_rxpath = './/../../figcaption'
        captions = table_element.xpath(self.caption_rxpath)

        if len(captions) > 0:
            self.parse_caption_label(captions[0], label=None)
            return

        # XPath of caption relative to the table element
        self.caption_rxpath = './/../../div[@class="Caption"]'
        captions = table_element.xpath(self.caption_rxpath)

        if len(captions) > 0:
            self.parse_caption_label(captions[0], label=None)
            return
