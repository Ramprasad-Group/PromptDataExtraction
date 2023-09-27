-- Select the DOIs from curated dataset where we have at least 10
-- paragraphs parsed.
-- Insert the selected DOIs into filtered_papers.
INSERT INTO filtered_papers (doi, filter_name, filter_desc, date_added)
SELECT doi,
'select-1k',
'Selected 1000 papers with >= 10 paras, including 630 from curated for pipeline tests.',
now() FROM (
	SELECT pt.doi, count(pt."text") FROM paper_texts pt 
	WHERE EXISTS (
		SELECT 1 FROM curated_data cd 
		WHERE cd.doi = pt.doi
	)
	GROUP BY pt.doi
	ORDER BY count
) AS dlist
WHERE count >= 10;

-- Randomly select the rest of the DOIs from polymer_papers
-- where we have at least 10 paragraphs parsed.
-- Insert the selected DOIs into filtered_papers.
INSERT INTO filtered_papers (doi, filter_name, filter_desc, date_added)
SELECT doi,
'select-1k',
'Selected 1000 papers with >= 10 paras, including 630 from curated for pipeline tests.',
now()
FROM (
	SELECT pt.doi, count(*) FROM paper_texts pt 
	JOIN filtered_papers fp ON fp.doi = pt.doi
	WHERE fp.filter_name = 'polymer_papers'
    AND fp.filter_name != 'select-1k'
	AND NOT EXISTS (
		SELECT 1 FROM curated_data cd 
		WHERE cd.doi = pt.doi
	)
	GROUP BY pt.doi
	ORDER BY random() 
	LIMIT 5000
) AS dlist
WHERE count >= 10
LIMIT 370;  -- This query may take a couple of minutes.

-- Verify that 1000 unique DOIs added to the table.
SELECT DISTINCT(fp.doi) FROM filtered_papers fp 
WHERE fp.filter_name = 'select-1k';
