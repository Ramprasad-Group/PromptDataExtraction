import pylogg

import frontend.resources as res
from backend.postgres import orm

log = pylogg.New('NEN')

class PolymerNorm:
    def __init__(self, name) -> None:
        self.name = name
        self.norm : orm.Polymers = None
        self.polymer : orm.Polymers = None

        db = res.postgres()
        self.polymer = orm.Polymers().get_one(db, {'name': self.name})
        if self.polymer:
            if self.polymer.is_norm:
                self.norm = self.polymer
            else:
                self.norm = orm.Polymers = orm.Polymers().get_one(
                    db, {'id': self.polymer.norm_id})

    @property
    def norm_name(self) -> str | None:
        return self.norm.name if self.norm else None

    @property
    def smiles(self) -> str | None:
        if self.polymer:
            return self.polymer.smiles
        else: return None
