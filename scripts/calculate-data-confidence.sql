-- DROP VIEW extracted_tg;
-- DROP VIEW data_score;

SELECT DISTINCT(fd.filter_name) FROM filtered_data fd;

CREATE OR REPLACE VIEW data_score AS
SELECT
	*,
	(unit + prop + tabl + rang) AS error,
	poly AS score
FROM (
	SELECT
		fd.target_id AS prop_id,
        -- negative attributes
		sum(CASE WHEN fd.filter_name = 'invalid_property_unit' 	THEN -1 ELSE 0 END) AS unit,
		sum(CASE WHEN fd.filter_name = 'invalid_property_name' 	THEN -1 ELSE 0 END) AS prop,
		sum(CASE WHEN fd.filter_name = 'is_table' 				THEN -1 ELSE 0 END) AS tabl,
		sum(CASE WHEN fd.filter_name = 'out_of_range' 			THEN -1 ELSE 0 END) AS rang,
        -- positive attributes
		sum(CASE WHEN fd.filter_name = 'is_polymer' 			THEN  1 ELSE 0 END) AS poly
	FROM filtered_data fd
	GROUP BY fd.target_id
) AS aggr;

SELECT * FROM data_score;
SELECT * FROM data_score ds WHERE ds.prop_id = 3704265;

CREATE OR REPLACE VIEW extracted_tg AS 
SELECT
	pt.doi,
	'GPT' AS "method",
	em.entity_name AS material,
	'Tg' AS property,
	ep.numeric_value AS value,
	ep.unit,
	ep.id AS prop_id,
	CASE
		WHEN ds.prop_id IS NOT NULL
		THEN ds.error ELSE 0
	END AS error,
	CASE
		WHEN ds.prop_id IS NOT NULL
		THEN ds.score ELSE 0
	END AS score
FROM extracted_properties ep 
JOIN extracted_materials em ON em.id = ep.material_id 
JOIN paper_texts pt ON pt.id = em.para_id 
LEFT JOIN data_score ds ON ep.id = ds.prop_id
WHERE ep.method_id = 180;

SELECT * FROM extracted_tg;
SELECT * FROM extracted_tg ed WHERE ed.error = 0;
