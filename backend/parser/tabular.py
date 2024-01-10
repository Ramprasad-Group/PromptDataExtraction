import re
import logging
import pandas as pd
from lxml import etree, html
from datetime import datetime
from ..text.normalize import innerText, normText

log = logging.getLogger("tabular")

class TableParser(object):

    # Mapping for database table
    _mapping = {
        'body': 'table_body',
        'tbl_header': 'header',
        'tbl_index': 'index'
    }

    def __init__(self) -> None:
        self.body = None
        self.header = None
        self.index = None
        self.caption = None
        self.notes = None
        self.descriptions = []
        self.number = None
        self.url = None
        self.dataframe = None
        self.date_added = datetime.now()

    @property
    def table_body(self):
        if self.body is None:
            return ""
        else:
            b = etree.tostring(self.body)
            return str(b, encoding="utf-8")

    def is_valid(self):
        return self.caption is not None
    
    def parse(self, table_element):
        self.body = table_element
        self.to_df() # build table df
        val = self.dataframe.iloc[0, :].values
        self.header = "\n".join([str(s) for s in val])
        val = self.dataframe.iloc[:, 1].values
        self.index = "\n".join([str(s) for s in val])
    
    def parse_number(self):
        regex = r"^Table (\d+|[IVXLCDM]+)[\.:]*"
        match = re.match(regex, self.caption, re.IGNORECASE)
        if match:
            self.number = match.group(1)

    def parse_caption_label(self, caption, label = None):
        text = ""

        # Label text
        if label is not None:
            text += innerText(label)
            
            # Add prefix to the caption
            if not text.lower().startswith("table"):
                text = "Table " + text

            text += " "
        
        # Caption text
        text += innerText(caption)
        
        # remove multiple spaces
        self.caption = re.sub(r'\s+', ' ', text).strip()

        # set table number
        self.parse_number()


    def __repr__(self) -> str:
        ret  = "\nTable " + str(self.number)
        ret += "\nCaption: " + str(self.caption)
        ret += "\nDescriptions: " + str(self.descriptions)
        return ret
    
    def save(self, outfile):
        """
        Save the raw HTML of the table body.

        """
        fp = open(outfile, "w+")
        html = etree.tostring(self.body, encoding="unicode", method='xml')
        fp.write(html)
        fp.write("\n")
        fp.write(self.caption)
        fp.close()
        print("Save OK: ", outfile)

    def to_df(self) -> pd.DataFrame:
        """
        Convert a table into pandas dataframe.
        
        """
        if self.dataframe is not None:
            return self.dataframe

        table = []
        block = 'tbody'
        row = None
        lastrowlen = None
        lastrowspan = 1
        col = 0
        spanset = [[0,0,""]] * 100   # initilize space for elements

        for tag in self.body.iter():
            # print(tag.tag, ": ", tag.text)

            try:
                # Get the tag name ignoring the namespace
                tag_name = tag.tag.split('}')[1] if '}' in tag.tag else tag.tag
            except:
                continue

            if tag_name == 'table':
                # table inside table
                table = []
                block = 'tbody'
                row = None
                lastrowlen = None
                lastrowspan = 1
                col = 0

            elif tag_name == 'thead':
                block = 'thead'

            elif tag_name == 'tbody':
                block = 'tbody'

            elif tag_name in ['tr', 'row']:
                if block is None:
                    raise ValueError("table block not set for ", self)

                if row is not None:
                    if lastrowlen is not None:
                        # catch this before pandas starts screaming
                        if len(row) != lastrowlen:
                            log.debug(f"WARN -- Table row not fully defined: {row}")
                            while len(row) < lastrowlen:
                                row.append("")

                    table.append(row)
                    lastrowlen = len(row)

                # Each row will record what type of row it is
                row = [block]
                col = 0
                # print("\nNew row ==============")

            elif tag_name in ['th', 'td', 'entry']:
                # Column Span
                colspan = tag.get('colspan')
                if colspan is None:
                    colspan = 1
                else:
                    colspan = int(colspan)

                # Row Span
                rowspan = tag.get('rowspan')
                if rowspan is None:
                    rowspan = 1
                else:
                    rowspan = int(rowspan)

                # Extract inner text
                # @Todo: use ^{} for sup and _{} for sub
                text = innerText(tag)
                if text is not None:
                    # convert to number if possible
                    try:
                        text = int(text)
                    except ValueError:
                        try:
                            text = float(text)
                        except ValueError:
                            pass

                # if prev rowspan was more than 1
                while spanset[col][0] > 1:
                    
                    # reduce rowspan by 1
                    spanset[col][0] = spanset[col][0] - 1

                    # add that cell colspan times
                    for _ in range(spanset[col][1]):
                        row.append(spanset[col][2])
                        col += 1


                # Add the current cell
                # print(col)
                for i in range(colspan):
                    row.append(text)
                    # Store for the next rows
                    spanset[col] = [rowspan, colspan, text]
                    col += 1
                # print(spanset)

        # Add the last row
        if row is not None:
            if spanset[col][0] > 1:
                for _ in range(spanset[col][1]):
                    row.append(spanset[col][2])
                spanset[col][0] = spanset[col][0] - 1
            
            # Add the cell
            for i in range(lastrowspan):
                table.append(row)

        # Use pandas to convert to jsonl
        self.dataframe = pd.DataFrame(table)
        return self.dataframe
    
    def to_jsonl(self) -> list[str]:
        """
        Convert a table into JSONL list of strings.
        
        """

        df = self.to_df()
        return df.to_json(orient='records', lines=True)

    @property
    def jsonl(self):
        return self.to_jsonl()



class XMLTableParser(TableParser):
    def __init__(self) -> None:
        # XPath of label and caption relative to the table element
        self.label_rxpath = './/*[local-name()="label"]'
        self.caption_rxpath = './/*[local-name()="caption"]'

        super().__init__()

    def parse(self, table_element):
        super().parse(table_element)

        labels = table_element.xpath(self.label_rxpath)
        captions = table_element.xpath(self.caption_rxpath)

        if len(captions) > 0:
            self.parse_caption_label(captions[0], labels[0])
