-- ------ Convert nm to eV for bandgap ------------
--------------------------------------------------------------------------------
-- Uncomment the Update statement to execute.
SELECT * FROM extracted_properties ep
--UPDATE extracted_properties ep 
--SET
--	unit = 'eV',
--	numeric_value = 1239.8 / ep.numeric_value,
--	numeric_error = 1239.8 / ep.numeric_error
WHERE   ep.method_id  = 175     -- method id for bandgap
AND     ep.unit = 'nm'          -- original unit
AND 	ep.numeric_error <> 0	-- avoid division by zero error
AND NOT EXISTS (                -- only the recognized bandgap properties
	SELECT 1 FROM filtered_data fd 
	WHERE fd.filter_name = 'invalid_property_name'
	AND fd.table_name = 'extracted_properties'
	AND fd.table_row = ep.id
);

-- ------ Convert meV to eV for bandgap ------------
--------------------------------------------------------------------------------
-- Uncomment the Update statement to execute.
SELECT * FROM extracted_properties ep
--UPDATE extracted_properties ep 
--SET
--	unit = 'eV',
--	numeric_value = ep.numeric_value / 1000.0,
--	numeric_error = ep.numeric_error / 1000.0
WHERE   ep.method_id  = 175     -- method id for bandgap
AND     ep.unit = 'meV'         -- original unit
AND NOT EXISTS (                -- only the recognized bandgap properties
	SELECT 1 FROM filtered_data fd 
	WHERE fd.filter_name = 'invalid_property_name'
	AND fd.table_name  = 'extracted_properties'
	AND fd.table_row = ep.id
);
