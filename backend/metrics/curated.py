import pylogg as log
from tqdm import tqdm
from sqlalchemy import text
from backend import postgres
from backend.postgres.orm import (
    PaperTexts, CuratedData, ExtractedMaterials, ExtractedProperties,
    ExtractionMethods
)


def compute_metrics(
        db, property_names : list[str], method : ExtractionMethods) -> dict:

    tp_mat = 0
    fp_mat = 0
    fn_mat = 0
    tp_val = 0
    fp_val = 0
    fn_val = 0
    tp_prop = 0
    fp_prop = 0
    fn_prop = 0

    log.note("Filtering data only for method = {}", method.name)

    # Select the curated paragraph that are also in the same method.
    query = """
        SELECT DISTINCT(cd.para_id) FROM extracted_materials em 
        JOIN curated_data cd ON cd.para_id = em.para_id 
        WHERE em.method_id = :method ORDER BY cd.para_id;
    """

    # SQL query for selecting materials of a para and method.
    mquery = """
        SELECT em.id, em.entity_name, em.coreferents
        FROM extracted_materials em 
        WHERE em.para_id = :para_id AND em.method_id = :method_id;
    """

    # SQL query for selecting properties of a material.
    pquery = """
        SELECT ep.entity_name, ep.value FROM extracted_properties ep 
        JOIN rel_material_properties rmp ON rmp.property_id = ep.id 
        WHERE ep.material_id = :material_id AND ep.method_id = :method_id;
    """

    items = postgres.raw_sql(query, method=method.id)

    log.note("Total {} paragraphs found from curated data.", len(items))

    n_ex_mat = 0
    n_ex_prop = 0
    n_curated = 0

    for item in tqdm(items):
        t2 = log.info("Processing paragraph: {}", item.para_id)

        curated_rows : list[CuratedData] = CuratedData().get_all(db, {
            'para_id':  item.para_id
        })

        log.info("Curated records: {}", len(curated_rows))

        ex_materials = postgres.raw_sql(
            mquery, method_id = method.id, para_id = item.para_id)
        
        log.trace("Extracted materials: {}", len(ex_materials))

        n_para_props = 0
        # Iterate over the curated/ground truth data.
        for cure in curated_rows:
            n_curated += 1
            val0 = cure.property_value
            if cure.property_name not in property_names:
                continue

            # Check the extracted materials against the curated one.
            material_found = False
            for material in ex_materials:
                if _material_match(cure.material, material.entity_name,
                    cure.material_coreferents, material.coreferents):
                    material_found = True

                ex_props = postgres.raw_sql(
                    pquery, method_id = method.id, material_id = material.id)

                # Check the extracted properties against the curated one.
                property_found = False
                for prop in ex_props:
                    val1 = prop.value
                    prop1 = prop.entity_name

                    if not _property_name_match(prop1, property_names):
                        continue

                    if _property_match(val0, val1):
                        property_found = True
                        break

                if property_found:
                    tp_val += 1
                    if material_found:
                        tp_prop += 1
                else:
                    fn_val += 1
                    if not material_found:
                        fn_prop += 1
                    log.warn("[FN] Value {} not found in extracted: {}",
                        val0, [(p.entity_name, p.value) for p in ex_props])

                if material_found:
                    break

            if material_found:
                tp_mat += 1
            else:
                fn_mat += 1
                log.warn("[FN] Material {} not found in extracted: {}",
                         cure.material,
                         [m.entity_name for m in ex_materials])

        # Iterate over the extracted data
        for material in ex_materials:
            n_ex_mat += 1
            # Check the curated materials against the extracted one.
            material_found = False
            for cure in curated_rows:
                if _material_match(
                    cure.material, material.entity_name,
                    cure.material_coreferents, material.coreferents):
                        material_found = True

            if not material_found:
                fp_mat += 1
                log.warn("[FP] Material {} not found in curated: {}",
                         material.entity_name,
                         [r.material for r in curated_rows])

            ex_props = postgres.raw_sql(
                pquery, method_id = method.id, material_id = material.id)

            n_para_props += len(ex_props)
            # breakpoint()

            for prop in ex_props:
                n_ex_prop += 1
                val1 = prop.value

                prop1 = prop.entity_name
                if not _property_name_match(prop1, property_names):
                    continue

                # Check the curated properties against the extracted one.
                property_found = False
                for cure in curated_rows:
                    if cure.property_name not in property_names:
                        continue

                    if _property_match(cure.property_value, val1):
                        property_found = True
                        break
                
                if not property_found:
                    fp_val += 1
                    log.warn("[FP] Value {} not found in curated: {}",
                        val1, [(r.property_name, r.property_value)
                               for r in curated_rows])
                    
                    if not material_found:
                        fp_prop += 1

        log.trace("Extracted properties: {}", n_para_props)
        t2.done("Paragraph {} processed.", item.para_id)

    db.close()

    log.note("Total curated properties: {}", n_curated)
    log.note("Total extracted materials: {}, properties: {}",
             n_ex_mat, n_ex_prop)

    mat_scores = _calc_scores(tp_mat, fp_mat, fn_mat)
    val_scores = _calc_scores(tp_val, fp_val, fn_val)
    prop_scores = _calc_scores(tp_prop, fp_prop, fn_prop)

    return {
        'method': method.name,
        'material': mat_scores,
        'value': val_scores,
        'property': prop_scores
    }


def _calc_scores(tp, fp, fn) -> dict:
    """ Returns precision, recall, F1 """
    if tp+fp>=0:
        precision = tp / (tp + fp)
    else:
        precision = 0

    if tp+fn>=0:
        recall = tp / (tp + fn)
    else:
        recall = 0

    if precision+recall>0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0

    return {
        'true_positives': tp,
        'false_positives': fp,
        'false_negatives': fn,
        'precision': precision,
        'recall': recall,
        'F1': f1,
    }


def _property_name_match(name : str, namelist : list[str]):
    criteria = [
        name in namelist,
        any([_norm_name(name) == _norm_name(n) for n in namelist])
    ]
    return any(criteria)

def _property_match(val0 : str, val1 : str):
    val0 = _norm_value(val0)
    val1 = _norm_value(val1)
    criteria = [
        # exact match
        val1 == val0,
        val1.replace(" to ", "-") == val0,
        val0.replace(" to ", "-") == val1,

        # fuzzy match
        val1 in val0,
        val0 in val1,
        val1 in val0.split(),
        val0 in val1.split(),
    ]
    return any(criteria)


def _material_match(
        mat0 : str, mat1 : str, mat0corefs : list[str], mat1corefs : list[str]):
    mat0 = _norm_name(mat0)
    corefs0 = [_norm_name(c) for c in mat0corefs]
    mat1 = _norm_name(mat1)
    corefs1 = [_norm_name(c) for c in mat1corefs]

    criteria = [
        # exact match
        mat1 == mat0,

        # fuzzy match
        len(mat1) > 2 and mat1 in mat0,
        len(mat0) > 2 and mat0 in mat1,

        # curated material name in extracted corefs
        any([mat0 == m.lower() for m in corefs1]),

        # extracted material name in curated corefs
        any([mat1 == m.lower() for m in corefs0])
    ]
    # log.debug(f"{any(criteria)} = {mat0} in {corefs1}, or {mat1} in {corefs0}")
    return any(criteria)

def _norm_value(val : str):
    val = val.lower()
    val = val.strip()
    val = val.replace(" ± ", "±")
    val = val.replace(" +/- ", "±")
    val = val.replace(" + /-", "±")
    val = val.replace(" +/-", "±")
    val = val.replace("+/-", "±")
    # val = val.replace(" ", '')
    val = val.replace('° C', '°C') # NER
    return val

def _norm_name(val : str):
    val = val.lower()
    val = val.strip()
    val = val.replace(" ", '')
    val = val.replace("α", "\\alpha")
    return val
