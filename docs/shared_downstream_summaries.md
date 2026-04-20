# Shared Downstream Summaries

## Purpose

This document defines the shared set of downstream summaries that will be generated from each cohort before any privacy-preserving release method is applied. These summaries are the common truth objects for all comparator methods.

The key design rule is:

Every comparator method must operate on the exact same site-truth summaries so that downstream differences reflect the masking strategy rather than different analytic inputs.

## Design Principles

The shared summary set should:

1. support geographic fidelity comparisons
2. support pooled statistical comparisons
3. expose sparse-cell behavior
4. be common across all three study populations
5. remain simple enough to be reproduced consistently across sites

The populations are:

1. all adult ICU hospitalizations
2. adult ICU sepsis
3. adult ICU cardiac arrest present on admission

## Summary Families

We should organize the common truth summaries into six families.

### Family 1: Cohort-Level Site Summary

This is the non-geographic anchor summary for each site and population.

Contents:

1. number of hospitalizations
2. number of unique patients
3. number and proportion with usable geography
4. admission year range
5. in-hospital mortality rate
6. median ICU length of stay
7. median hospital length of stay if available

Why it matters:

1. supports pooled descriptive validation
2. provides a stable denominator for operational and statistical checks
3. allows easy method comparison without geographic sparsity dominating the result

### Family 2: County Burden Summary

This is the main geographic truth summary.

Unit:

`county × year × population`

Contents:

1. number of eligible hospitalizations
2. number of deaths
3. mortality proportion
4. number missing county
5. observation coverage metadata if needed

Why it matters:

1. directly supports map-based and county-rank validation
2. works for all three populations
3. creates the main stress test for sparse-cell masking behavior

### Family 3: County Standardization Summary

This summary supports geographic standardization and pooled demographic comparisons.

Unit:

`county × year × age_band × sex × population`

Contents:

1. hospitalization count
2. death count

Why it matters:

1. supports age-sex standardized county rates
2. allows fair comparison of geographic burden after demographic adjustment
3. is a realistic high-dimensional table that challenges masking methods

This should be the primary standardized geographic summary because it is rich enough to be useful but still more portable than full county-by-race-by-ethnicity tables.

### Family 4: Non-Geographic Demographic Summary

This summary supports pooled disparity analyses without exploding the geographic key space.

Unit:

`year × age_band × sex × race_group × ethnicity_group × population`

Contents:

1. hospitalization count
2. death count

Why it matters:

1. supports statistical fidelity testing for subgroup summaries
2. keeps high-dimensional demographics out of the county table
3. mirrors the successful design logic already used in your ARF pollution attribution workflow

### Family 5: Outcome Severity Summary

This summary creates a shared, non-map-based severity comparison across methods.

Unit:

`site × year × population`

Contents:

1. hospitalization count
2. death count
3. ICU LOS median
4. ICU LOS upper quartile
5. proportion with prolonged ICU LOS based on a fixed threshold

Why it matters:

1. tests whether masking distorts common severity summaries
2. supports pooled statistical comparison without county-level sparsity
3. is easy to compute across all populations

### Family 6: Inference-Ready Modeling Summary

This summary is the smallest common object needed for downstream pooled modeling.

Recommended first model:

County-year mortality burden model for each population, with optional external county-level exposures or social vulnerability measures linked centrally.

Unit:

`county × year × population`

Core fields:

1. hospitalization count
2. death count
3. age-sex standardized denominators derived from Family 3
4. site indicator
5. optional county-level external covariates added centrally after release

Why it matters:

1. allows end-to-end inference comparison across methods
2. keeps model inputs aligned with the main geographic scientific use case
3. avoids requiring patient-level or record-level pooled data

## Shared Outcomes

To ensure fairness across populations, the primary shared outcome set should be small and universal.

### Primary Shared Outcomes

1. hospitalization count
2. in-hospital death count
3. in-hospital mortality proportion

### Secondary Shared Outcomes

1. ICU length of stay summary
2. hospital length of stay summary if consistently derivable
3. hospice or death combined outcome if sites use it consistently

The primary cross-method comparison should focus first on counts and mortality, because they are the most portable and least dependent on site-specific derivation choices.

## Shared Geographic Scales

The common truth summaries should support at least two geographic scales.

### Primary Geographic Scale

1. county

### Secondary Geographic Scale

1. state

State-level outputs can be derived from county truth summaries for coarsening comparisons, so they do not require a separate upstream cohort pipeline.

## Shared Time Scale

The default temporal resolution should be:

1. admission year

This keeps the initial study design manageable and comparable across all populations. If needed later, admission quarter can be added as a sensitivity analysis.

## Shared Demographic Categories

The common grouped variables should be:

1. age band
2. sex
3. race group
4. ethnicity group

Recommended age bands:

1. 18 to 39
2. 40 to 64
3. 65 to 74
4. 75 and older

These match the need for transportable cross-site summaries without over-fragmenting the data.

## Minimum Common Summary Set

If we want the leanest fair comparison set for the first pass, it should include exactly these four truth summary objects per population:

1. site cohort summary
2. county-year burden summary
3. county-year age-sex summary
4. year age-sex race-ethnicity summary

This is the recommended first-pass shared set because it is enough to evaluate:

1. overall pooled descriptive fidelity
2. county-level geographic fidelity
3. demographic standardization
4. subgroup statistical fidelity
5. sparse-cell robustness

## Recommended First-Pass Analytic Targets

Using the minimum common summary set, we can compare methods on:

1. pooled total hospitalizations
2. pooled deaths and mortality
3. county ranking and hotspot agreement
4. age-sex standardized county mortality
5. pooled demographic disparities in mortality

## What To Exclude From The First Pass

To keep the method comparison fair and tractable, the first-pass shared summary set should exclude:

1. patient-level trajectories
2. complex time-to-event curves
3. very high-dimensional county-by-race-by-ethnicity tables
4. cluster-based phenotyping summaries

Those can be added later as extension experiments, but they are not needed to establish whether deterministic masking is superior on the main geographic and statistical objectives.

## Recommendation

The study should begin with the minimum common summary set and treat it as the official truth layer for all comparator methods. Once the methods are performing well on that layer, we can expand to richer summaries if needed.
