# Keys Directory

This folder stores deterministic masking key fragments returned to a site from the external key-generation website.

## What Goes Here

The site should place the downloaded fragment CSV files directly in this folder.

Expected filename patterns:

- `key_county_year_Fragment_*.csv`
- `key_county_year_age_sex_Fragment_*.csv`
- `key_year_age_sex_race_ethnicity_Fragment_*.csv`

Examples:

- `key_county_year_Fragment_A.csv`
- `key_county_year_age_sex_Fragment_B.csv`
- `key_year_age_sex_race_ethnicity_Fragment_A.csv`

The pipeline discovers these files automatically based on the filename pattern.

## Template Copies

Local template copies may exist under `keys/templates/`, but that folder is ignored by Git and is not part of the finalized site deliverables.

## Important Notes

- Do not rename fragment files unless the filename still matches the expected pattern.
- Keep only the current site’s fragment files in this folder when preparing a site release.
- These files are required for the `det_offset` release method.
- The other release methods do not require key fragments.

## Related Documentation

- [Project overview](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/README.md)
- [Site workflow](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/code/README.md)
