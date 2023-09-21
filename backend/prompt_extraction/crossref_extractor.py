import re
import pylogg
from rapidfuzz import process
from chemdataextractor.doc import Paragraph

from backend.postgres import persist
from backend.text.normalize import TextNormalizer
from backend.postgres.orm import PaperTexts, ExtractedCrossrefs

log = pylogg.New('llm')


class CrossrefExtractor:
    RE_ABBR = r'\s\(([^\s]+?)\)\s?'
    MAX_PRECEEDING = 5

    def __init__(self, db) -> None:
        self.db = db
        self.normalizer = TextNormalizer()
        self.abbr2full = {} # Can be any reference, not just abbreviations.
        self.full2abbr = {} # Can be any reference, not just abbreviations.


    def process_paragraph(self, para : PaperTexts):
        """ Populate list of cross reference for a given paragraph,
            via parsing or from database.
        """
        self.abbr2full = {}
        self.full2abbr = {}

        self._load_crossrefs(para)
        self._find_abbr(para.text)
        self.save_crossrefs(para)


    def list_all(self, text : str, fuzzy_cutoff : int = 96) -> list[str]:
        """ Return the list of all fuzzy matches with the text.
            Includes source (abbr) and destination (full form) matches.
        """
        # Check against the list of known abbreviations.
        matches = process.extract(
            text, list(self.abbr2full.keys()), score_cutoff=fuzzy_cutoff)

        # Check against the list of known full forms.
        matches = process.extract(
            text, list(self.full2abbr.keys()), score_cutoff=fuzzy_cutoff)
        
        return [match[0] for match in matches]


    def _load_crossrefs(self, para : PaperTexts):
        """ Query the database to load all the cross refs of this paper. """
        refs : list[ExtractedCrossrefs] = ExtractedCrossrefs().get_all(
            self.db, {'paper_id': para.pid})
        for ref in refs:
             self.abbr2full[ref.name] = ref.othername

        self.db.close()
        log.trace("Added {} cross-refs from database.", len(refs))


    def _find_abbr(self, text : str):
        """ Find and add all abbreviation pairs from the given text. """

        para = Paragraph(text)
        abbreviations = para.abbreviation_definitions
        for abbrpair in abbreviations:
            full = self.normalizer.norm_chars(" ".join(abbrpair[1]))
            for abbr in abbrpair[0]:
                if len(abbr) == 1:
                    continue
                self.full2abbr[full] = abbr
                self.abbr2full[abbr] = full

        # Manually add the other ones not detected by CDE.
        i = 0
        for match in re.finditer(self.RE_ABBR, text):
            abbr = match.group(0).lstrip(" (").rstrip(") ")
            if not re.search(r'[a-zA-Z]', abbr):
                # Ignore pure numbers.
                continue

            if len(abbr) < 2:
                continue

            if abbr in self.abbr2full or abbr in self.full2abbr:
                i = match.span()[1]
                continue
            else:
                j = match.span()[0]
                preceding_words = text[i:j].split()
                nchars = min(len(abbr), self.MAX_PRECEEDING)
                full = " ".join(preceding_words[-nchars:]).strip()
                self.full2abbr[full] = abbr
                self.abbr2full[abbr] = full
                i = match.span()[1]


    def save_crossrefs(self, para : PaperTexts):
        """
            Save parsed abbreviations and cross references to database.
        """
        t3 = log.trace("Saving cross-references.")
        n = 0
        for k, v in self.abbr2full.items():
            if persist.add_crossref(self.db, para, k, v, 'abbr'):
                n += 1
        
        for k, v in self.full2abbr.items():
            if persist.add_crossref(self.db, para, k, v, 'abbr'):
                n += 1

        self.db.commit()
        self.db.close()
        t3.done("Saved {} cross-references for paragraph: {}", n, para.id)
