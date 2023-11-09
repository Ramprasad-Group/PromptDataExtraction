-- ------ Convert nm to eV for bandgap ------------
--------------------------------------------------------------------------------
-- Uncomment to view the rows first.
-- SELECT * FROM extracted_properties ep
UPDATE extracted_properties ep 
SET
	unit = 'eV',
	numeric_value = 1239.8 / ep.numeric_value
WHERE   ep.method_id  = 175     -- method id for bandgap
AND     ep.unit = 'nm'          -- original unit
AND NOT EXISTS (                -- only the recognized bandgap properties
	SELECT 1 FROM filtered_data fd 
	WHERE fd.filter_name = 'invalid_property_name'
	AND fd.target_table = 'extracted_properties'
	AND fd.target_id = ep.id
);

-- ------ Convert meV to eV for bandgap ------------
--------------------------------------------------------------------------------
-- Uncomment to view the rows first.
-- SELECT * FROM extracted_properties ep
UPDATE extracted_properties ep 
SET
	unit = 'eV',
	numeric_value = ep.numeric_value / meV
WHERE   ep.method_id  = 175     -- method id for bandgap
AND     ep.unit = 'meV'         -- original unit
AND NOT EXISTS (                -- only the recognized bandgap properties
	SELECT 1 FROM filtered_data fd 
	WHERE fd.filter_name = 'invalid_property_name'
	AND fd.target_table = 'extracted_properties'
	AND fd.target_id = ep.id
);
