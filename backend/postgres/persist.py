import pylogg
from . import orm

log = pylogg.New("persist")

def add_crossref(db, para : orm.PaperTexts, name : str, othername : str,
                   reftype : str) -> bool :
    """ Add a cross reference to the database.
        Returns false if already exists.
    """
    log.trace("Adding {} cross-ref for paper {}: {} = {}",
              reftype, para.pid, name, othername)
    
    ref = orm.ExtractedCrossrefs().get_one(
        db, {'name': name, 'reftype': reftype})

    if ref is None:
        ref = orm.ExtractedCrossrefs()
        ref.paper_id = para.pid
        ref.para_id = para.id
        ref.name = name
        ref.othername = othername
        ref.reftype = reftype

        ref.insert(db)
        return True
    
    return False
