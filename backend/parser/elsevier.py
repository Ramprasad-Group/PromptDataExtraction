from .document import XMLDocumentParser


class ElsevierParser(XMLDocumentParser):
    def __init__(self, filepath) -> None:
        super().__init__('elsevier', filepath)

        # Elsevier XML specific configs
        self.table_xpath = '//*[local-name()="table"]'
        self.date_xpath = '//*[local-name()="vor-load-date"]'
        self.journal_xpath = '//*[local-name()="srctitle"]'

    def parse_meta(self):
        super().parse_meta()

        # If date not found
        if self.date.strip() == "":
            self.date_xpath = '//*[local-name()="cover-date-end"]'
            self.date = self.xpath_to_string(self.date_xpath)
        
        # If date not found
        if self.date.strip() == "":
            self.date_xpath = '//*[local-name()="cover-date-orig"]'
            self.date = self.xpath_to_string(self.date_xpath)
        
        # If date not found
        if self.date.strip() == "":
            self.date_xpath = '//*[local-name()="cover-date-start"]'
            self.date = self.xpath_to_string(self.date_xpath)


    def parse_paragraphs(self):
        self.para_xpath = '//*[local-name()="para"]'
        return super().parse_paragraphs()