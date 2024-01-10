import pylogg as logger


def compute_metrics(ground_truth: dict, extracted: dict):
    """
        Compute the metrics for the extracted data against a ground truth data.
        The datasets must of type:
        ```
        {
            doi: [
                {'material': 'P1', 'material_coreferents': ['P1'], 'property_value': '1 ° C'}
                {'material': 'P2', 'material_coreferents': ['P2'], 'property_value': '2 ° C'}
            ]
        }
        ```
        Returns precision, recall, f1 and list of dois with error
    """
    tp, fp, fn, tn = 0, 0, 0, 0
    error_doi_set = set()

    for doi, item_list in ground_truth.items():
        extracted_list = extracted.get(doi, None)
        if extracted_list is not None:
            for record in item_list:
                material_coreferents = record['material_coreferents']
                property_value = str(record['property_value'])
                for item in extracted_list:
                    t3 = logger.trace("Comparing: {} against {}", item, record)
                    extracted_property_value = item['property_value']
                    if type(item['material']) is not str:
                        logger.info(
                            f"material key is not a string for {doi} {item['material']}")
                        continue
                    if extracted_property_value is not None and extracted_property_value != 'N/A':
                        extracted_property_value = extracted_value_postprocessing(
                            extracted_property_value)
                        if extracted_property_value is None:
                            logger.info(
                                f'Extracted property value is not a string or a well formed dict for {doi}: {extracted_property_value}')
                            continue
                        property_flag = compare_property_value(
                            extracted_property_value, property_value)
                        material_flag = any([entity_postprocess(item['material']) in entity_postprocess(material) or entity_postprocess(
                            material) in entity_postprocess(item['material']) for material in material_coreferents])
                        if material_flag and property_flag:  # Fuzzier notion of matching
                            tp += 1
                            t3.done("Match found")
                            break
                        elif property_flag:
                            logger.info(
                                f'For {doi} and {item["material"]} property value match {extracted_property_value} but material entity does not match. True coreferents {material_coreferents}')
                        elif material_flag:
                            logger.info(
                                f'For {doi} material entities match: {item["material"]} but property value does not match. True property value: {property_value}; Extracted property value: {extracted_property_value}')

                else:
                    fn += 1
                    error_doi_set.add(doi)
                    logger.info(f'False negative for DOI {doi}: {record}')
        else:
            fn += len(item_list)
            error_doi_set.add(doi)
            logger.info(
                f'False negative: {item_list}, DOI {doi} not in extracted dataset')

    for doi, item_list in extracted.items():
        ground_truth_list = ground_truth[doi]
        for item in item_list:
            # material = item['material']
            extracted_property_value = item['property_value']
            if extracted_property_value is not None and extracted_property_value != 'N/A':
                extracted_property_value = extracted_value_postprocessing(
                    extracted_property_value)
                if extracted_property_value is None:
                    logger.info(
                        f'Extracted property value is not a string or a well formed dict for {doi}: {extracted_property_value}')
                    fp += 1
                    error_doi_set.add(doi)
                    continue
                # Check if the extracted data has the same material coreferents
                for record in ground_truth_list:

                    logger.trace("Comparing: {} against {}", item, record)
                    property_value = str(record['property_value'])
                    # break_flag = compare_property_value(extracted_property_value, property_value)
                    if any([
                        entity_postprocess(
                            item['material']) in entity_postprocess(material)
                        or entity_postprocess(material) in entity_postprocess(item['material'])
                        for material in record['material_coreferents']
                    ]):
                        if compare_property_value(extracted_property_value, property_value):
                            break
                else:
                    fp += 1
                    error_doi_set.add(doi)
                    logger.info(f'False positive: {item} for DOI {doi}')
            else:
                fp += 1
                error_doi_set.add(doi)
                logger.info(f'False positive: {item} for DOI {doi}')

    if tp+fp >= 0:
        precision = tp / (tp + fp)
    else:
        precision = 0
    if tp+fn >= 0:
        recall = tp / (tp + fn)
    else:
        recall = 0
    if precision+recall > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0

    logger.info(f'True negatives: {tn}')
    logger.info(f'True positives: {tp}')
    logger.info(f'False negatives: {fn}')
    logger.info(f'False positives: {fp}')
    logger.info(f'Precision: {precision}')
    logger.info(f'Recall: {recall}')
    logger.info(f'F1: {f1}')

    return precision, recall, f1, list(error_doi_set)


def extracted_value_postprocessing(extracted_property_value):
    if type(extracted_property_value) is str:
        extracted_property_value = property_postprocessing(
            extracted_property_value)
    elif type(extracted_property_value) is dict and all([type(val) is str for val in extracted_property_value.values()]):
        logger.info(
            f'Extracted property value is dict: {extracted_property_value}')
        extracted_property_value = [property_postprocessing(
            val) for val in extracted_property_value.values()]
    elif type(extracted_property_value) is int or type(extracted_property_value) is float:
        extracted_property_value = str(extracted_property_value)
    elif type(extracted_property_value) is list and all([type(val) is str for val in extracted_property_value]):
        pass

    else:
        extracted_property_value = None

    return extracted_property_value


def property_postprocessing(property_value: str) -> str:
    """ Normalize property unit. """
    property_value = property_value.replace('°C', '° C')
    return property_value


def entity_postprocess(entity: str) -> str:
    """ Normalize entity name. """
    entity = entity.replace(' ', '').lower()
    return entity


def compare_property_value(extracted_property_value, property_value) -> bool:
    break_flag = False
    if type(extracted_property_value) is str:
        if property_value in extracted_property_value or extracted_property_value in property_value:
            break_flag = True
    elif type(extracted_property_value) is list:
        for ex in extracted_property_value:
            if entity_postprocess(property_value) in entity_postprocess(ex) or entity_postprocess(ex) in entity_postprocess(property_value):
                break_flag = True
                break
    return break_flag
