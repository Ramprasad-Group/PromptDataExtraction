"""
    Module to compute material, property and material-property F1 scores.

    Algorithm:
        G = Curated ground truth from the `curated_data` table.
        E = Extracted data using a specific method/pipeline.

        Gr = Rows of G that matches the property name.
        Er = Rows of E that matches the property name.

        for e in Er:
            if e in Gr, then TP, else FP.

        for g in Gr:
            if g NOT in Er, then FN.

        TN = 0 since G does not have negative values.

    Notes:
        (1) Because there are many duplicates, the number of matches will be
        different while iterating over the curated rows vs. iterating over
        the extracted rows.

        (2) Self-consistency check: F1-score must be 1.0 when the E = G. Use
        this for validation, tests and debugging.

"""

from dataclasses import dataclass

import pylogg as log
from tqdm import tqdm
from backend import postgres
from backend.postgres.orm import ExtractionMethods

@dataclass
class Counter:
    tp_mat : int = 0
    fp_mat : int = 0
    fn_mat : int = 0
    tp_val : int = 0
    fp_val : int = 0
    fn_val : int = 0
    tp_prop : int = 0
    fp_prop : int = 0
    fn_prop : int = 0

    # Distinct paragraphs from the curated rows.
    para_from_curated : int = 0

    # There are extracted rows not associated with curated paragraphs.
    relevant_extracted_rows : int = 0

    # Extracted and relevant rows that matches the property.
    prop_extracted_rows : int = 0

    # How many materials, values and (materials,values) are found in curated.
    mat_matched_iter_extracted : int = 0
    mat_not_matched_iter_extracted : int = 0
    val_matched_iter_extracted : int = 0
    val_not_matched_iter_extracted : int = 0
    prop_matched_iter_extracted : int = 0
    prop_not_matched_iter_extracted : int = 0

    total_curated_rows : int = 0
    prop_curated_rows : int = 0

    # How many materials, values and (materials,values) are found in extracted.
    mat_matched_iter_curated : int = 0
    mat_not_matched_iter_curated : int = 0
    val_matched_iter_curated : int = 0
    val_not_matched_iter_curated : int = 0
    prop_matched_iter_curated : int = 0
    prop_not_matched_iter_curated : int = 0

    def log_all(self):
        log.note("Summary stats:")
        for f in self.__dataclass_fields__:
            log.note("{}: {}", f, self.__dict__[f])


def compute_singular_metrics(property_names : list[str],
                             method : ExtractionMethods) -> dict:

    n = Counter()
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
    n.para_from_curated = len(items)
    log.note("Total {} paragraphs found from curated data.",
             n.para_from_curated)

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

    # Uncomment to perform the self-consistency check.
    # extracted_sql = curated_sql

    for item in tqdm(items):
        t2 = log.info("Processing paragraph: {}", item.para_id)

        curated_rows = postgres.raw_sql(curated_sql, para_id = item.para_id)
        extracted_rows = postgres.raw_sql(
            extracted_sql, method_id = method.id, para_id = item.para_id)
        
        log.info("Total curated records: {}", len(curated_rows))
        log.info("Total extracted records: {}", len(extracted_rows))

        n.total_curated_rows += len(curated_rows)
        n.relevant_extracted_rows += len(extracted_rows)

        # Find TP, FP
        for extr in extracted_rows:
            if not _property_name_match(extr.property_name, property_names):
                continue

            n.prop_extracted_rows += 1
            value_found = False
            material_found = False
            property_found = False

            for cure in curated_rows:
                if not _property_name_match(cure.property_name, property_names):
                    continue

                # General property value match.
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
                n.tp_mat += 1
                n.mat_matched_iter_extracted += 1
            else:
                n.fp_mat += 1
                n.mat_not_matched_iter_extracted += 1
                log.info("[FP] Material '{}' not found in curated: {}",
                         extr.material, [r.material for r in curated_rows])

            if value_found:
                n.tp_val += 1
                n.val_matched_iter_extracted += 1
            else:
                n.fp_val += 1
                n.val_not_matched_iter_extracted += 1
                log.info("[FP] Value '{}' not found in curated: {}",
                         extr.property_value, [
                             (r.property_name, r.property_value)
                             for r in curated_rows])

            if property_found:
                n.tp_prop += 1
                n.prop_matched_iter_extracted += 1
            else:
                n.fp_prop += 1
                n.prop_not_matched_iter_extracted += 1
                if material_found:
                    log.info("[FP] Property material '{}' matches, "
                             "value '{}' does not match.", extr.material,
                             extr.property_value)
                elif property_found:
                    log.info("[FP] Property value '{}' matches, "
                             "material '{}' does not match.",
                             extr.property_value, extr.material)
                else:
                    log.info("[FP] Property material '{}' and "
                             "value '{}' do not match.", extr.material,
                             extr.property_value)


        # Find FN
        for cure in curated_rows:
            if not _property_name_match(cure.property_name, property_names):
                continue

            n.prop_curated_rows += 1
            value_found = False
            material_found = False
            property_found = False

            for extr in extracted_rows:
                if not _property_name_match(extr.property_name, property_names):
                    continue

                # General property value match.
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
                n.fn_mat += 1
                n.mat_not_matched_iter_curated += 1
                log.info("[FN] Material '{}' not found in extracted: {}",
                         cure.material, [r.material for r in extracted_rows])
            else:
                n.mat_matched_iter_curated += 1

            if not value_found:
                n.fn_val += 1
                n.val_not_matched_iter_curated += 1
                log.info("[FN] Value '{}' not found in extracted: {}",
                         cure.property_value, [
                             (r.property_name, r.property_value)
                             for r in extracted_rows])
            else:
                n.val_matched_iter_curated += 1

            if not property_found:
                n.fn_prop += 1
                n.prop_not_matched_iter_curated += 1
                if material_found:
                    log.info("[FN] Property material '{}' matches, "
                             "value '{}' does not match.", cure.material,
                             cure.property_value)
                elif property_found:
                    log.info("[FN] Property value '{}' matches, "
                             "material '{}' does not match.",
                             cure.property_value, cure.material)
                else:
                    log.info("[FN] Property material '{}' and "
                             "value '{}' do not match.", cure.material,
                             cure.property_value)
            else:
                n.prop_matched_iter_curated += 1

        t2.done("Paragraph {} processed.", item.para_id)

    mat_scores = _calc_scores(n.tp_mat, n.fp_mat, n.fn_mat)
    val_scores = _calc_scores(n.tp_val, n.fp_val, n.fn_val)
    prop_scores = _calc_scores(n.tp_prop, n.fp_prop, n.fn_prop)

    n.log_all()

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
