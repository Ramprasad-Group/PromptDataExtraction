import sett
import json
from backend import postgres
from backend.postgres.orm import PaperSections
from sqlalchemy import func

sett.load_settings()

postgres.load_settings()
db = postgres.connect()

# results = db.query(PaperSections).all()

skip_headers = ['related', 'supporting information', 'request username', 'password changed successfully',
                'information', 'figures', 'acknowledgements', 'acknowledgement', 'terms & conditions',
                'conflict of interest', 'conflicts of interest', 'supporting information available', 'notes',
                'declaration of interest', 'rights and permissions', 'about this article', 'references',
                'references and notes', 'author information', 'additional information', 'funding sources',
                'credit authorship contribution statement', 'funding', 'fundings', 'declaration of conflicting interests',
                'competing interests', 'conflict-of-interest disclosure', 'authorship contribution statement',
                'authorship', 'authorship contributions and disclosure of conflicts of interest',
                'abbreviations', 'availability of supporting data', 'funding information', 'authorship statement',
                'author statement', 'disclosures', 'disclosure of potential conflicts of interest',
                'statement of conflicts', 'statement of conflict of interest', 'uncited references',
                'electronic supplementary material', 'ethics declarations', 'copyright', 'author contributions',
                'supplementary materials', 'supplementary data', 'supplementary files', 'appendix a. supplementary data',
                'supplementary information', 'authors contribution', 'conflict of interest statement',
                'disclosure', 'financial interest']

doi_counts = (db.query(PaperSections.doi, PaperSections.func.count(PaperSections.doi))
              .filter(~PaperSections.name.in_(skip_headers))
              .group_by(PaperSections.doi)
              .all()
              )


# for doi, count in doi_count_less_than_5:
#     print(f"DOI: {doi}, Count: {count}")

result = [{"doi": doi, "count": count} for doi, count in doi_counts if count < 3]

# output_filename = "doi_error.json"
# with open(output_filename, "w") as json_file:
#     json.dump(result, json_file, indent=4)

print(f"Number of DOIs extracted improperly: {len(result)}")