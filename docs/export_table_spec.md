# Export Table Specification

## Goal

These are the actual site-level export tables that should be produced from the shared truth summaries and then released under each comparator method. The key design choice is that sites should build one canonical truth layer first, and every privacy method should transform the same truth tables.

The export package should therefore contain:

1. a common truth-table schema defined once
2. one method-specific released version of each common table
3. a lightweight metadata manifest

## Populations

Each export table must carry a `population_id` field with one of:

1. `all_icu_adult`
2. `sepsis_ase_icu`
3. `cardiac_arrest_poa_icu`

This lets us keep a consistent table family across all three cohorts.

## Core Export Families

Sites should send four primary export families. These come directly from the shared summary layer already implemented in `code/02_shared_summaries.py`.

### Table 1: Site Cohort Summary

Purpose:

1. pooled descriptive validation
2. operational benchmarking
3. non-geographic statistical fidelity checks

Primary key:

1. `site_name`
2. `population_id`

Columns:

1. `site_name`
2. `population_id`
3. `n_hospitalizations`
4. `n_patients`
5. `n_with_geo`
6. `pct_with_geo`
7. `admission_year_min`
8. `admission_year_max`
9. `death_n`
10. `mortality_pct`
11. `icu_los_hours_median`
12. `icu_los_hours_q3`
13. `prolonged_icu_los_n`
14. `prolonged_icu_los_pct`

Recommended filename pattern:

`site_cohort_summary_<method_id>_<site_name>.csv`

### Table 2: County-Year Burden Summary

Purpose:

1. county-level mapping
2. county ranking and hotspot validation
3. pooled burden modeling

Primary key:

1. `site_name`
2. `population_id`
3. `county_fips`
4. `admit_year`

Columns:

1. `site_name`
2. `population_id`
3. `county_fips`
4. `admit_year`
5. `hospitalizations`
6. `deaths`
7. `mortality_pct`
8. `missing_county_hospitalizations`

Recommended filename pattern:

`county_year_burden_summary_<method_id>_<site_name>.csv`

### Table 3: County-Year Age-Sex Summary

Purpose:

1. age-sex standardization
2. fairness across methods for adjusted geographic comparisons
3. sparse-cell stress testing

Primary key:

1. `site_name`
2. `population_id`
3. `county_fips`
4. `admit_year`
5. `age_band`
6. `sex_group`

Columns:

1. `site_name`
2. `population_id`
3. `county_fips`
4. `admit_year`
5. `age_band`
6. `sex_group`
7. `hospitalizations`
8. `deaths`
9. `mortality_pct`

Recommended filename pattern:

`county_year_age_sex_summary_<method_id>_<site_name>.csv`

### Table 4: Year Age-Sex Race-Ethnicity Summary

Purpose:

1. pooled subgroup disparity analyses
2. non-geographic high-dimensional testing
3. fairness across methods without exploding the county key space

Primary key:

1. `site_name`
2. `population_id`
3. `admit_year`
4. `age_band`
5. `sex_group`
6. `race_group`
7. `ethnicity_group`

Columns:

1. `site_name`
2. `population_id`
3. `admit_year`
4. `age_band`
5. `sex_group`
6. `race_group`
7. `ethnicity_group`
8. `hospitalizations`
9. `deaths`
10. `mortality_pct`

Recommended filename pattern:

`year_age_sex_race_ethnicity_summary_<method_id>_<site_name>.csv`

## Method-Specific Release Rules

Each comparator should release the same four tables, but transformed according to the method.

## Method A: Deterministic Offset Masking

Method id:

`det_offset`

Release rule:

1. apply deterministic positive offsets to all count columns in each table
2. use one externally created site-specific key file per table
3. use the same offset for all count columns in a given cell
4. leave non-count descriptive columns untouched unless they are derivable from counts, in which case they should be recomputed centrally after demasking

For this method, the exported count columns are:

1. `n_hospitalizations`
2. `n_patients`
3. `n_with_geo`
4. `death_n`
5. `prolonged_icu_los_n`
6. `hospitalizations`
7. `deaths`
8. `missing_county_hospitalizations`

Important rule:

Percentages and rates should not be relied on as released values for deterministic masking. Sites may include them for QC, but the coordinating center should recompute them after pooling and demasking from the count columns.

## Method B: Small-Cell Suppression

Method id:

`suppress_lt10`

Release rule:

1. suppress all count cells with counts below 11
2. apply complementary suppression where simple back-calculation would reveal suppressed values
3. set derived percentages or rates to missing where suppressed counts prevent valid calculation

In this repository's initial implementation, suppressed cells are labeled as `"<10"` in the released count columns rather than left blank.

Important rule:

Suppression should act on count columns only. Non-count descriptive values that become inferable from counts should also be suppressed when necessary.

## Method C: Random Cell Perturbation

Method id:

`rand_unif_3`

Release rule:

1. add an independent discrete uniform perturbation from minus 3 to plus 3 to each count cell
2. truncate perturbed counts below zero to zero
3. recompute percentages and rates from the perturbed counts locally before export

Important rule:

This method should be repeated multiple times for evaluation, so the manifest must include a `replicate_id`.

## Method D: Geographic Coarsening

Method id:

`state_coarsen`

Release rule:

1. aggregate county-level tables to state level before release
2. keep the same non-geographic site and demographic tables
3. include `state_fips` instead of `county_fips` in the coarsened geographic tables

Important rule:

This method intentionally discards county-level signal and serves as a structural comparator, not a cell-masking comparator.

## Shared Manifest

Each site package should include one manifest that describes every released table.

Recommended manifest filename:

`site_export_manifest_<site_name>.csv`

Columns:

1. `site_name`
2. `population_id`
3. `method_id`
4. `table_family`
5. `file_name`
6. `n_rows`
7. `release_level`
8. `replicate_id`
9. `mask_version`
10. `notes`

Recommended values:

1. `release_level` is `site`, `county`, `state`, or `demo`
2. `replicate_id` is blank except for random perturbation runs
3. `mask_version` is populated for deterministic offset masking

## Common Column Rules

To make pooling easy, every export table should follow these conventions.

1. `site_name` always included
2. `population_id` always included
3. year column always named `admit_year`
4. county geography always named `county_fips`
5. state geography always named `state_fips`
6. count columns are non-negative integers
7. percentages are proportions on the 0 to 1 scale

## What The Coordinating Center Uses

For pooled comparisons, the coordinating center should prioritize counts, not percentages, from the released tables.

Truth-comparison workflow:

1. pool count columns across sites
2. demask pooled deterministic tables where applicable
3. recompute rates, percentages, and standardized summaries centrally
4. compare method-specific pooled outputs against pooled truth

## Recommended First-Pass Site Package

For the first validation round, each site should release:

1. 4 truth tables for internal local benchmarking only
2. 4 deterministic masked tables
3. 4 suppression tables
4. 4 random perturbation tables for each replicate
5. 4 state-coarsened tables
6. 1 manifest

This gives a compact but complete site return package for fair cross-method comparison.
