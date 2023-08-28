from tabular import TableParser
from document import HTMLDocumentParser


class IOPParser(HTMLDocumentParser):
    """HTML Parser for IOP publications. ECS and IOP have similar HTML structures.
    """

    def __init__(self, filepath) -> None:
        super().__init__('iop_publishing', filepath)
        self.tableParser = _iopTableParser

        # Meta
        self.journal_xpath = '//span[@itemid="periodical"]'
        self.date_xpath = '//span[@class="wd-jnl-art-pub-date"]'
        self.body_xpath = '//div[@class="article-content"]'

    def _full_table_links(self, tree) -> list:
        a_elements = []
        return a_elements


class _iopTableParser(TableParser):
    def __init__(self) -> None:
        super().__init__()

    def parse(self, table_element):
        super().parse(table_element)

        # XPath of caption relative to the table element
        self.caption_rxpath = './/../p'
        captions = table_element.xpath(self.caption_rxpath)

        if len(captions) > 0:
            self.parse_caption_label(captions[0], label=None)
