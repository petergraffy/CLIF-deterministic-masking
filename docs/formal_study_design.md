# Formal Study Design

## Study Overview

This study is a multicenter federated validation of deterministic masking for geographically stratified aggregate CLIF analyses. The goal is to determine whether deterministic masking preserves scientific utility better than alternative privacy-preserving release methods while maintaining acceptable protection for low-count cells and acceptable operational burden for participating sites.

The study is designed as a repeated within-site and pooled-between-site comparison. Each participating site will derive the same cohorts and the same downstream summaries from local CLIF data, then apply multiple privacy-preserving release methods to identical truth tables. Released outputs will be pooled centrally and compared against pooled truth generated from the original unmasked site-level summaries.

## Data Source And Setting

The source data are site-local CLIF v2.1.0 tables. Cohorts and downstream summaries are constructed locally at each site using a shared analytic codebase. No patient-level data are transferred outside the originating institution. Only aggregate outputs produced from the common protocol are shared for central comparison and pooled analysis.

The design explicitly leverages CLIF geography fields available in the `hospitalization` table, including `county_code`, `census_tract`, and ZIP-based fields, because one of the main scientific advantages of this masking approach is support for geographically resolved federated research.

## Study Populations

The validation will be performed across three pre-specified populations.

### Population 1: All Adult ICU Hospitalizations

This cohort includes adult hospitalizations with at least one ICU stay in the admission window.

Purpose:

1. provide a broad denominator cohort
2. benchmark operational performance under high-volume conditions
3. evaluate masking behavior in relatively dense geographic cells

### Population 2: Adult ICU Sepsis Cohort

This cohort includes adult ICU hospitalizations meeting CDC Adult Sepsis Event criteria, implemented through the CLIFpy ASE algorithm.

Purpose:

1. test masking performance for a complex multi-table phenotype
2. evaluate preservation of clinically meaningful derived counts and rates
3. assess pooled inference under a nontrivial cohort definition

### Population 3: Cardiac Arrest Present On Admission

This cohort includes adult ICU hospitalizations with a cardiac arrest diagnosis flagged present on admission in `hospital_diagnosis`.

Purpose:

1. test masking performance in a sparser, high-severity cohort
2. evaluate preservation of geographic hotspots and rare-event burden patterns
3. stress-test privacy behavior in low-count cells

This cohort should be described in the manuscript as `cardiac arrest present on admission`, not confirmed out-of-hospital cardiac arrest, unless additional validation rules are added later.

## Study Design

This is a comparative methodological study with five nested comparison levels.

### Level 1: Within-Site Truth Versus Released Output

At each site, a truth version of each downstream summary table will be generated from local CLIF data. The same truth table will then be transformed by each privacy-preserving release method. This allows direct measurement of method-specific distortion before pooling.

### Level 2: Across-Method Comparison

For every cohort and every downstream summary, each privacy method will be evaluated against the same site-level truth. This makes the comparison internally controlled and avoids confounding by cohort definition or analyst workflow.

### Level 3: Central Pooled Recovery

Released site outputs will be pooled centrally according to the common protocol. For deterministic masking, pooled demasking will occur centrally before final inference. Final pooled results from each method will be compared against the pooled truth obtained from the original unmasked site-level summaries.

### Level 4: Scenario-Based Robustness Testing

Each method will be re-evaluated under pre-specified stress conditions, including sparse-cell settings, partial site participation, and alternative geographic granularity.

### Level 5: Repeated Release Stability

Methods with randomness will be run repeatedly on the same truth tables to measure release instability. Deterministic methods will be tested for exact reproducibility.

## Primary Endpoints

The primary endpoints are grouped into four domains.

### Geographic Endpoints

1. county-level count error
2. county-level rate error
3. county rank concordance
4. hotspot classification agreement
5. preservation of spatial autocorrelation

### Statistical Endpoints

1. pooled count recovery
2. pooled subgroup proportion recovery
3. regression coefficient bias
4. standard error distortion
5. agreement in final scientific conclusions

### Privacy Endpoints

1. recoverability of low-count cells
2. susceptibility to differencing attacks
3. susceptibility to repeated-release attacks
4. masking margin for sparse cells

### Operational Endpoints

1. runtime and memory burden
2. failure rate
3. usable-cell retention
4. reproducibility
5. analytic complexity for sites and coordinating center

## Secondary Endpoints

Secondary endpoints will assess:

1. method performance by population
2. method performance by true cell size
3. method performance by site size
4. method performance by geographic granularity
5. sensitivity of pooled model estimates to release strategy

## Experimental Workflow

The workflow is fixed before export schema design.

1. Build the three study populations locally from CLIF data
2. Construct pre-specified truth summary tables for each population
3. Apply each privacy-preserving release method to the same truth summaries
4. Pool site returns centrally
5. Demask pooled deterministic outputs where applicable
6. Compare method-specific pooled outputs against pooled truth
7. Repeat the evaluation under robustness scenarios

## Robustness Scenarios

The following scenarios are pre-specified.

### Sparse-Cell Scenario

Evaluate method performance across true cell sizes:

1. 0 to 5
2. 6 to 10
3. 11 to 25
4. more than 25

### Partial Site Participation Scenario

Evaluate pooled performance under:

1. all sites
2. random 80% of sites
3. random 50% of sites
4. large sites only
5. mixed large and small site subsets

### Geographic Granularity Scenario

Evaluate method performance for:

1. county-level outputs
2. state-level outputs
3. coarsened regional groupings if used in sensitivity analyses

### Repeated Release Scenario

Repeat the same release multiple times on the same truth input to quantify run-to-run instability for random methods.

## Hypothesis Framework

The primary hypothesis is that deterministic masking will outperform comparator methods in end-to-end geographic and statistical fidelity while retaining acceptable privacy protection and better operational reproducibility.

More specifically, deterministic masking is expected to:

1. preserve pooled truth more accurately after central demasking
2. preserve county-level scientific signal better than suppression-heavy or random-noise methods
3. retain more analyzable cells than suppression-heavy methods
4. produce exact or near-exact reproducibility across repeated runs

## Interpretation Framework

The deterministic method will be considered superior if it demonstrates:

1. lower pooled geographic and statistical error than comparator methods
2. equal or better retention of analyzable cells
3. acceptable privacy behavior for low-count cells
4. reproducible outputs under repeated runs
5. acceptable performance under realistic partial-site and sparse-cell scenarios

## Planned Reporting

The manuscript methods should report:

1. cohort definitions
2. privacy methods compared
3. shared downstream summary specifications
4. primary and secondary endpoints
5. robustness scenarios
6. pooled comparison approach

The results should report:

1. broad cohort and site participation characteristics
2. method performance for geography
3. method performance for pooled inference
4. method performance for privacy and operations
5. failure modes and scenario-specific weaknesses
