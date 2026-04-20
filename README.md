# CLIF Deterministic Masking Validation

This repository validates a deterministic masking workflow for geographically resolved, federated CLIF analyses. The project is designed to support a JAMIA-style methods paper comparing deterministic offset masking against common alternatives for site-level release of aggregate ICU summaries.

## Project Aim

We want to show that deterministic masking can preserve scientific usability better than common alternatives while still supporting distributed data sharing across sites. The validation framework compares four release methods:

- `det_offset`: deterministic positive offsets applied with external site-specific key fragments and central demasking
- `suppress_lt10`: small-cell suppression using `<10`
- `rand_unif_3`: bounded random perturbation of count cells
- `state_coarsen`: geographic coarsening from county to state with post-coarsening `<10` suppression

## Study Populations

The site pipeline constructs three CLIF populations:

- `all_icu_adult`: all adult ICU hospitalizations
- `sepsis_ase_icu`: adult ICU hospitalizations meeting the CLIFpy Adult Sepsis Event definition
- `cardiac_arrest_poa_icu`: adult ICU hospitalizations with cardiac arrest present on admission

## Required CLIF Tables

The current workflow uses these CLIF tables:

- `patient`
- `hospitalization`
- `adt`
- `hospital_diagnosis`
- `microbiology_culture`
- `medication_admin_intermittent`
- `medication_admin_continuous`
- `labs`
- `respiratory_support`

The sepsis cohort depends on `clifpy`, which reads the CLIF source tables directly during Adult Sepsis Event computation.

## What The Site Produces

After a full run, the site produces:

- a site-level Table 1 summary in [output/final/tables](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/output/final/tables)
- method-specific site export packages in [output/final/site_exports](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/output/final/site_exports)

The final export folders are:

- [det_offset](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/output/final/site_exports/det_offset)
- [suppress_lt10](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/output/final/site_exports/suppress_lt10)
- [rand_unif_3](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/output/final/site_exports/rand_unif_3)
- [state_coarsen](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/output/final/site_exports/state_coarsen)

Transient logs and shared-summary exports are intentionally cleaned up and not retained as part of the finalized site deliverables.

## Current Site-Facing Workflow

The site-facing code is a single entrypoint:

```bash
./.venv/bin/python code/site_pipeline.py all
```

That command:

1. builds the three cohorts
2. creates a site-level Table 1 summary
3. creates all four release packages

Additional details for site execution, environment setup, and key fragment download are in [code/README.md](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/code/README.md).

## Key Fragment Architecture

Deterministic masking uses external key fragments placed in [keys](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/keys). The current pipeline expects these fragment families:

- `key_county_year_Fragment_*.csv`
- `key_county_year_age_sex_Fragment_*.csv`
- `key_year_age_sex_race_ethnicity_Fragment_*.csv`

These fragments are matched automatically by filename. Rates are not demasked directly; they are blanked in released deterministic outputs for central recomputation after demasking.

## Publication-Facing Outputs

This repository is set up to support:

- site-level baseline characterization via Table 1 outputs
- method-specific export generation for each participating site
- pooled coordinating-center evaluation of geographic fidelity, statistical fidelity, sparse-cell behavior, and reproducibility

The main design and methods notes live in [docs](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/docs), including:

- [formal_study_design.md](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/docs/formal_study_design.md)
- [comparator_methods_spec.md](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/docs/comparator_methods_spec.md)
- [export_table_spec.md](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/docs/export_table_spec.md)

## Configuration

Site-specific configuration lives in `config/config.json` and is ignored by Git. The required fields are just `site_name`, `repo`, `tables_path`, and `file_type`. See [config/README.md](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/config/README.md) and [config/config_template.json](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/config/config_template.json).
