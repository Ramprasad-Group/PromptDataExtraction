from tqdm import tqdm
from backend import sett, postgres
from backend.postgres.orm import Polymers
from backend.utils import jsonl

sett.load_settings()
postgres.load_settings()

db = postgres.connect()

# Load current name list.
namelist = jsonl.read_file(sett.DataFiles.polymer_namelist_jsonl)
dbitems : list[Polymers] = Polymers().get_all(db)
db.close()

print(f"Loaded {len(namelist)} jsonl items, {len(dbitems)} database items.")

newlist = []
n = 0
for i, line in enumerate(tqdm(namelist)):
    name = line['polymer']
    newline = None

    for dbitem in dbitems:
        # print("Check", name, "\t==>\t", dbitem.name)
        if dbitem.name.lower() == name or dbitem.norm_name.lower() == name:
            newline = {
                'polymer': name,
                'is_norm': dbitem.is_norm,
                'normalized_name': dbitem.norm_name,
                'is_polymer': dbitem.is_polymer,
                'is_copolymer': dbitem.is_copolymer,
                'is_composite': dbitem.is_composite,
                'is_blend': dbitem.is_blend,
            }
            n += 1
            break

    if newline:
        newlist.append(newline)
    else:
        newlist.append(line)

    if i%500 == 0:
        print("Processed", i, "items. Found", n, "normalized polymers.")


n = 0
for i, item in enumerate(tqdm(dbitems)):
    existing = False
    for line in namelist:
        name = line['polymer']
        if name == item.name.lower() or name == item.norm_name.lower():
            existing = True
            n += 1
            break

    if not existing:
        newline = {
            'polymer': item.name,
            'is_norm': item.is_norm,
            'normalized_name': item.norm_name,
            'is_polymer': item.is_polymer,
            'is_copolymer': item.is_copolymer,
            'is_composite': item.is_composite,
            'is_blend': item.is_blend,
        }
        newlist.append(newline)

    if i%500 == 0:
        print("Processed", i, "items. Found", n, "new polymers.")


jsonl.save_file(newlist, sett.DataFiles.polymer_namelist_jsonl)
print("Done! Found", n, "new normalized polymers.")
