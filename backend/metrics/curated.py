import pylogg as log
from tqdm import tqdm
from backend import postgres
from backend.postgres.orm import CuratedData, ExtractionMethods


def compute_singular_metrics(property_names : list[str],
                             method : ExtractionMethods) -> dict:

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
        SELECT DISTINCT(cd.para_id) FROM curated_data cd 
        WHERE EXISTS (
            SELECT 1 FROM filtered_paragraphs fp 
            WHERE fp.para_id = cd.para_id
            AND fp.filter_name = :filter_name
        );
    """
    items = postgres.raw_sql(query, filter_name = method.para_subset)
    log.note("Total {} paragraphs found from curated data.", len(items))

    curated_sql = """
        -- Curated data of a paragraph.
        SELECT
            cd.material,
            cd.material_coreferents,
            cd.property_name,
            cd.property_value
        FROM curated_data cd 
        WHERE cd.para_id = :para_id;
    """

    extracted_sql = """
        -- Extracted data of a paragraph.
        SELECT
            em.entity_name AS material,
            em.coreferents AS material_coreferents,
            ep.entity_name AS property_name,
            ep.value AS property_value
        FROM extracted_properties ep 
        JOIN extracted_materials em ON em.id = ep.material_id 
        WHERE ep.method_id = :method_id
        AND em.para_id = :para_id;
    """

    n_ex = 0
    n_gn = 0

    for item in tqdm(items):
        t2 = log.info("Processing paragraph: {}", item.para_id)

        curated_rows = postgres.raw_sql(curated_sql, para_id = item.para_id)
        extracted_rows = postgres.raw_sql(
            extracted_sql, method_id = method.id, para_id = item.para_id)
        
        log.info("Total curated records: {}", len(curated_rows))
        log.info("Total extracted records: {}", len(extracted_rows))

        # Find TP, FP
        for extr in extracted_rows:
            if not _property_name_match(extr.property_name, property_names):
                continue

            n_ex += 1
            value_found = False
            material_found = False
            property_found = False

            for cure in curated_rows:
                if not _property_name_match(cure.property_name, property_names):
                    continue

                if _property_match(cure.property_value, extr.property_value):
                    value_found = True

                match = _material_match(
                    cure.material, extr.material, cure.material_coreferents,
                    extr.material_coreferents)

                if match:
                    material_found = True
                    # Must check for this specific row.
                    if _property_match(cure.property_value,
                                       extr.property_value):
                        property_found = True

            if material_found:
                tp_mat += 1
            else:
                fp_mat += 1
                log.info("[FP] Material '{}' not found in curated: {}",
                         extr.material, [r.material for r in curated_rows])

            if value_found:
                tp_val += 1
            else:
                fp_val += 1
                log.info("[FP] Value '{}' not found in curated: {}",
                         extr.property_value, [
                             (r.property_name, r.property_value)
                             for r in curated_rows])

            if property_found:
                tp_prop += 1
            else:
                fp_prop += 1
            


        # Find FN
        for cure in curated_rows:
            if not _property_name_match(cure.property_name, property_names):
                continue

            n_gn += 1
            value_found = False
            material_found = False
            property_found = False

            for extr in extracted_rows:
                if not _property_name_match(extr.property_name, property_names):
                    continue

                if _property_match(cure.property_value, extr.property_value):
                    value_found = True

                match = _material_match(
                    cure.material, extr.material, cure.material_coreferents,
                    extr.material_coreferents)

                if match:
                    material_found = True
                    # Must check for this specific row.
                    if _property_match(cure.property_value,
                                       extr.property_value):
                        property_found = True

            if not material_found:
                fn_mat += 1
                log.info("[FN] Material '{}' not found in extracted: {}",
                         cure.material, [r.material for r in extracted_rows])

            if not value_found:
                fn_val += 1
                log.info("[FN] Value '{}' not found in extracted: {}",
                         cure.property_value, [
                             (r.property_name, r.property_value)
                             for r in extracted_rows])

            if not property_found:
                fn_prop += 1

        t2.done("Paragraph {} processed.", item.para_id)

    log.note("Property curated records: {}", n_gn)
    log.note("Property extracted records: {}", n_ex)

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
