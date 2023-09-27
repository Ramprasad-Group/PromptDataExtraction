
-- Reset the pkey sequences as the number of rows available.

SELECT setval('rel_material_properties_id_seq', cnt.next_id) FROM (
	SELECT count(*)+1 AS next_id FROM rel_material_properties rmp 
) as cnt;

SELECT setval('extracted_material_amounts_id_seq', cnt.next_id) FROM (
	SELECT count(*)+1 AS next_id FROM extracted_material_amounts ema  
) as cnt;

SELECT setval('extracted_materials_id_seq', cnt.next_id) FROM (
	SELECT count(*)+1 AS next_id FROM extracted_materials
) as cnt;

SELECT setval('extracted_properties_id_seq', cnt.next_id) FROM (
	SELECT count(*)+1 AS next_id FROM extracted_properties
) as cnt;
