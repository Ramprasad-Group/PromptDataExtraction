from .tabular import TableParser
from .document import HTMLDocumentParser


class RSCParser(HTMLDocumentParser):
    def __init__(self, filepath) -> None:
        super().__init__('rsc', filepath)
        self.tableParser = _rscTableParser

        # RSC puts figures into tables !!
        self.table_xpath = '//table[contains(@class, "tgroup")]'

        # Meta
        self.title_xpath = '//h1'
        self.journal_xpath = '//div[@class="article_info"]//span[@class="italic"]/a'
        self.date_xpath = '//p[@class="abstract"]/preceding-sibling::p[1]'
        self.abstract_xpath = '//p[@class="abstract"]'
        self.body_xpath = '//div[@id="wrapper"]'


    def _full_table_links(self, tree) -> list:
        a_elements = []
        return a_elements

    def parse_meta(self):
        super().parse_meta()

        # If date not found
        if self.abstract.strip() == "":
            self.date_xpath = '//div[@class="abstract"]/preceding-sibling::p[1]'
            self.abstract_xpath = '//div[@class="abstract"]'
            self.date = self.xpath_to_string(self.date_xpath)
            self.abstract = self.xpath_to_string(self.abstract_xpath)
    
    def parse_paragraphs(self):
        self.para_xpaths = ['//p', '//span']
        return super().parse_paragraphs()


class _rscTableParser(TableParser):
    def __init__(self) -> None:
        super().__init__()

    def parse(self, table_element):
        super().parse(table_element)

        # XPath of caption relative to the table element
        self.caption_rxpath = './/../../preceding-sibling::div[@class="table_caption"][1]'
        captions = table_element.xpath(self.caption_rxpath)

        if len(captions) > 0:
            self.parse_caption_label(captions[0], label=None)
