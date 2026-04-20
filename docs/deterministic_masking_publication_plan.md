# Deterministic Masking Validation: CLIF-to-Publication Blueprint

## Project Frame

This repository is currently structured as a standard CLIF project template. The scientific work for this project should turn that template into a reproducible validation study for the masking approach already used in the ARF pollution attribution workflow: sites create aggregate exports from CLIF, apply deterministic positive offsets using external site-specific keys, and a coordinating center later demasks after pooling.

The working end product is a JAMIA-style manuscript built from:

1. a transparent CLIF-based cohort construction workflow
2. a deterministic offset-masking pipeline applied consistently across sites
3. a validation framework that compares true, masked, and demasked aggregate outputs
4. a publication-ready set of aggregate tables, figures, and supplementary methods

## Proposed Study Aim

Primary aim:
Evaluate whether deterministic offset masking of site-level aggregate CLIF exports preserves pooled descriptive and inferential results after demasking closely enough to support distributed critical care research.

Secondary aims:

1. Quantify distortion introduced by masking before and after pooled demasking
2. Identify which exported table designs are robust versus fragile under deterministic offsets
3. Define practical acceptance thresholds for publication-grade analytic equivalence

## Core Study Questions

The paper should answer a small set of concrete questions:

1. Do masked site exports remain non-identifying while still supporting valid pooled estimation?
2. After demasking, do pooled counts, rates, and effect estimates recover the true values?
3. How sensitive are results to table granularity and key dimensionality?
4. What happens when some sites contribute and others do not, given that demasking occurs after pooling?
5. Can sites run the workflow locally and share only masked aggregate outputs plus QC summaries?

## CLIF-Based Build Strategy

### Phase 1: Specify the validation use cases

Pick 2 to 4 representative export-and-analysis tasks that stress different parts of CLIF. A strong set would include:

1. Cohort identification using `hospitalization`, `patient`, and `adt`
2. Time-varying physiology using `vitals` and `labs`
3. Device trajectory analysis using `respiratory_support`
4. Treatment exposure analysis using `medication_admin_continuous`

The publication is stronger if masking is validated across multiple common aggregate export patterns rather than just one table.

### Phase 2: Define the true, masked, and demasked pipelines

For every analysis task, run the workflow in three representations:

1. True site-level aggregate tables derived from original CLIF
2. Masked site-level aggregate tables after deterministic offsets
3. Pooled demasked tables at the coordinating center

The important distinction from ordinary de-identification studies is that the masking acts on exported cells, not on raw patient-level CLIF tables. Validation therefore needs to compare:

1. true site aggregate versus masked site aggregate
2. pooled true aggregate versus pooled demasked aggregate
3. final manuscript estimates from the true versus demasked pooled data

### Phase 3: Compare exports and pooled outputs, not patient-level records

The repository should produce aggregate validation artifacts that compare true, masked, and demasked outputs on:

1. Cohort counts
2. Missingness
3. Distribution summaries
4. Event counts and outcome numerators or denominators
5. Post-stratification margins
6. Regression or prediction model outputs from pooled demasked data

## Recommended Analysis Architecture

The current template already suggests the right top-level workflow. We should make it concrete as:

1. `01_cohort_identification`
   Build the target analytic cohort from CLIF source tables and save cohort IDs plus cohort summary metrics.
2. `02_project_quality_checks`
   Check schema completeness, category harmonization, missingness, implausible dates, duplication, and site-specific anomalies.
3. `03_outlier_handling`
   Apply project-defined outlier logic consistently before downstream comparison.
4. `04_project_analysis`
   Generate masked-versus-unmasked validation metrics, figures, and manuscript tables.

From a study design perspective, the key addition is that each step should be aware of `data_version = true`, `masked`, or `demasked`.

## Suggested Directory-Level Deliverables

The repo should evolve toward producing these outputs:

### Intermediate outputs

1. `output/intermediate/cohort_summary_true_<site>.csv`
2. `output/intermediate/export_table_true_<table>_<site>.csv`
3. `output/intermediate/export_table_masked_<table>_<site>.csv`
4. `output/intermediate/qc_report_<version>_<site>.csv`

### Final outputs

1. `site_masking_distortion_<site>.csv`
2. `pooled_demasking_recovery.csv`
3. `model_agreement_true_vs_demasked.csv`
4. `masking_validation_dashboard.pdf`
5. `manuscript_results_overview.txt`

## Validation Metrics To Pre-Specify

This is the heart of the paper. We should decide these before running the study.

### Cohort fidelity

1. Absolute and percent difference in exported cell counts
2. Distortion-to-signal ratio for small versus large cells
3. Agreement in cohort-defining numerators or denominators after demasking

### Data fidelity

1. Whether every expected cell is present in the key and export
2. Mean absolute masking increment by table
3. Correlation between true and demasked aggregate summaries
4. Preservation of category totals after pooling and demasking

### Temporal fidelity

1. Recovery of year-level and other time-binned totals after demasking
2. Stability of any trajectory-derived summaries after aggregation
3. Bias introduced when sparse cells are heavily offset
4. Sensitivity to alternative grouping choices before export

### Modeling fidelity

1. Change in regression coefficients and confidence intervals using true versus demasked pooled tables
2. Change in attributable fractions, rates, or other target estimands
3. Subgroup stability after post-stratification demasking
4. Any failure modes when offset keys are mismatched or partial site returns occur

### Practical acceptance criteria

Examples to define up front:

1. Demasked pooled cell counts exactly recover the true pooled counts when all required keys are present
2. Manuscript effect estimates from demasked pooled data differ from true pooled estimates only within a pre-specified tolerance
3. No masked site export reveals true small cells directly
4. Table design remains workable for sites and coordinator without explosive key size

These exact thresholds need project consensus, but the manuscript should clearly state them a priori.

## Minimal CLIF Tables Likely Needed

The exact list depends on the chosen use cases, but a high-yield core set is:

1. `patient`
2. `hospitalization`
3. `adt`
4. `vitals`
5. `labs`
6. `respiratory_support`
7. `medication_admin_continuous`

Optional extensions:

1. `medication_admin_intermittent`
2. `microbiology`
3. `intake_output`
4. `procedures`

## Manuscript Shape For JAMIA

### Introduction

Frame the paper around the need for privacy-preserving, multi-site critical care analytics using harmonized EHR data. Position deterministic offset masking of aggregate exports as an operational solution that must be validated for analytic integrity before widespread CLIF use.

### Methods

Methods should have five tight subsections:

1. Data source and CLIF harmonization
2. Deterministic offset-masking approach and external key design
3. Cohort definitions and analysis tasks
4. Validation metrics and acceptance thresholds
5. Multi-site execution and aggregate result sharing

### Results

A clean results sequence would be:

1. Cohort flow and site participation
2. Properties of masked site exports
3. Recovery of pooled counts and descriptive statistics after demasking
4. Agreement in downstream analyses using true versus demasked pooled data
5. Operational feasibility across participating sites

### Discussion

Focus on:

1. What aspects of analytic validity were preserved
2. Where masking and demasking introduced measurable distortion
3. Which export designs appear safe versus more fragile
4. Implications for federated CLIF studies and reproducible aggregate data sharing

## Immediate Repo Priorities

To move from template to study-ready repository, the next implementation steps should be:

1. Replace placeholder README language with the deterministic masking study objective
2. Add a project-specific `config/config.json` schema that separates source CLIF paths, masked export paths, and pooled demasked inputs
3. Turn the template scripts into real project scripts with shared helper functions for key joins and offset application
4. Define the exported table schemas and corresponding key dimensions first
5. Pre-specify the primary recovery metrics and acceptance thresholds in code and prose
6. Build manuscript-ready table and figure exporters into `04_project_analysis`

## Recommended First Analysis

Start with one narrow but publication-relevant validation analysis:

1. Adult ICU hospitalizations over a fixed date range
2. One core site-year or site-condition table with a manageable key space
3. One post-stratification table such as age-sex or race-ethnicity
4. One downstream pooled model or rate estimate derived from the demasked aggregates

This gives us a manageable first end-to-end run and a convincing prototype for the paper.

## Working Assumptions

This blueprint assumes:

1. Sites have access to original CLIF data locally
2. Patient-level data cannot be pooled centrally
3. Sites export only aggregate tables plus QC summaries
4. Offset keys are created externally, are site-specific, and match the exported table dimensions exactly
5. Coordinating-center demasking happens only after masked site outputs are returned

## Definition Of Success

This project is ready for a JAMIA-style submission when the repository can:

1. reproduce the same cohort logic across sites from original CLIF data
2. export masked site-level aggregate tables in a standardized format
3. recover the true pooled aggregates through the demasking workflow
4. generate manuscript tables and figures from true-versus-demasked comparisons
5. support a clear claim about when deterministic aggregate masking is and is not analytically acceptable
