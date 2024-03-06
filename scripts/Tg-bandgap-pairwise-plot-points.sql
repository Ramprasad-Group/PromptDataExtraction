-- All extracted Tg and Bandgap data for the marked points in pairwise plot.
-- Uncomment a where clause below to fetch point specific data.

SELECT 0 AS "point", ed."method", ed.material, ed.property, ed.value, ed.unit
FROM extracted_data ed 
JOIN extracted_properties ep ON ep.id = ed.property_id
--WHERE ed.doi = '10.1007/s10854-007-9344-z' 	-- Point 1: Svorcik_2008, SI Ref. 2.
--WHERE ed.doi = '10.1039/d1ee02630e' 			-- Point 2: Deshmukh_2022, SI Ref. 3.
--WHERE ed.doi = '10.1038/pj.2010.116' 			-- Point 3: Lee_2011, SI Ref. 4.
--WHERE ed.doi = '10.1039/C5RA03529E' 			-- Point 4: Terraza_2015, SI Ref. 5.
--WHERE ed.doi = '10.1016/j.msec.2019.01.081' 	-- Point 5: Ponnamma_2019, SI Ref. 6.
--WHERE ed.doi = '10.1002/mame.200300013' 		-- Point 6: Hu_2003, SI Ref. 7.
AND (ed.property = 'tg' OR ed.property = 'bandgap');

