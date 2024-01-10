from .tabular import TableParser
from .document import HTMLDocumentParser


class HindawiParser(HTMLDocumentParser):
    def __init__(self, filepath) -> None:
        super().__init__('hindawi', filepath)
        self.tableParser = _hindawiTableParser

        # Hindawi puts table inside another table
        self.table_xpath = '//table[@class="table-group"]'

        # Meta
        self.title_xpath = '//h1'
        self.journal_xpath = '//div[@id="journal__navigation"]/a'
        self.date_xpath = '//div[contains(@class, "articleContent__PublicationTimeLineWrapper")]/div[1]/span[2]'
        self.abstract_xpath = '//article[contains(@class, "article_body")]//div[@class="xml-content"]//p[1]'
        self.body_xpath = '//article[contains(@class, "article_body")]'

    def _full_table_links(self, tree) -> list:
        # Hindawi can have links to full tables (ex. tab1/, tab2/ etc.)
        a_elements = []

        for i in range(1, 51):
            full_links = tree.xpath('//a[@href="tab%d/"]' %i)
            if len(full_links) > 0:
                a_elements += full_links
            else:
                # if tab1/ is not found, tab2/ will not be found either
                break
        
        return a_elements
    
    def parse_meta(self):
        super().parse_meta()

        if self.journal.strip() == "":
            self.journal_xpath = '//h1[@class="banner_title"]'
            self.journal = self.xpath_to_string(self.journal_xpath)
            self.title_xpath = '//h2'
            self.title = self.xpath_to_string(self.title_xpath)

        if self.abstract.strip() == "":
            self.abstract_xpath = '//h4[text()="Abstract"]/following-sibling::p'
            self.abstract = self.xpath_to_string(self.abstract_xpath)

        if self.body.strip() == "":
            self.body_xpath = '(//div[@class="xml-content"])[2]'
            self.body = self.xpath_to_string(self.body_xpath)

        if self.date.strip() == "":
            self.date_xpath = '(//div[@class="xml-content"])[1]/preceding-sibling::p[2]'
            self.date = self.xpath_to_string(self.date_xpath)
    
    def parse_paragraphs(self):
        self.para_xpaths = ['//*[local-name()="p"]']
        return super().parse_paragraphs()


class _hindawiTableParser(TableParser):
    def __init__(self) -> None:
        super().__init__()

    def parse(self, table_element):
        super().parse(table_element)

        # XPath of caption relative to the table element

        caption_rxpath = './/../../../div[@class="floats-partial-footer"]'
        captions = table_element.xpath(caption_rxpath)

        if len(captions) > 0:
            self.parse_caption_label(captions[0], label=None)
            return
        
        # For full text links
        caption_rxpath = './/../../div[@class="groupcaption"]'
        captions = table_element.xpath(caption_rxpath)

        if len(captions) > 0:
            self.parse_caption_label(captions[0], label=None)
