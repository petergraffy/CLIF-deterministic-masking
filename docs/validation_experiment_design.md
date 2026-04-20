# Deterministic Masking Validation Experiment Design

## Study Objective

We will evaluate whether deterministic masking of geographically stratified aggregate outputs preserves scientific validity better than competing privacy-preserving release strategies while maintaining acceptable disclosure protection and operational feasibility.

The target use case is federated CLIF research in which each site computes local aggregate outputs from CLIF tables, releases only masked aggregates, and pooled analyses are performed centrally.

## Study Populations

We will evaluate masking performance across three populations that represent different cohort construction burdens and different expected sparsity patterns.

1. All adult ICU hospitalizations
2. Adult ICU hospitalizations meeting CDC Adult Sepsis Event criteria
3. Adult ICU hospitalizations with cardiac arrest present on admission

These populations intentionally span:

1. a broad high-volume denominator cohort
2. a multi-table derived phenotype
3. an acute diagnosis-based cohort that is likely to produce sparse geographic cells

## Comparator Methods

The primary comparison set should include:

1. Deterministic offset masking with external site-specific keys and central demasking
2. Small-cell suppression
3. Random perturbation of cell counts
4. Geographic coarsening alone, such as county-to-state or multi-county region aggregation

If resources are limited, prioritize the first three.

## Core Evaluation Domains

We should evaluate each method in four main domains and one robustness domain.

### 1. Geographic Fidelity

Question:
Does the released data preserve the spatial signal needed for mapping, burden estimation, and geographic ranking?

Primary metrics:

1. Absolute and relative error in county-level counts and rates
2. Correlation between true and released county-level rates
3. County ranking concordance, such as Spearman correlation and top-decile overlap
4. Hotspot classification agreement
5. Preservation of spatial autocorrelation statistics such as Moran's I
6. Preservation of exposure-response gradients after linking county-level external data

### 2. Statistical Fidelity

Question:
Does masking preserve descriptive and inferential results?

Primary metrics:

1. Error in pooled counts, proportions, and standardized rates
2. Error in subgroup summaries by age, sex, race, or ethnicity
3. Bias in regression coefficients and standard errors
4. Confidence interval overlap and coverage
5. Agreement in effect direction and statistical conclusion
6. Calibration of downstream predictions if any predictive analyses are run

### 3. Privacy Resistance

Question:
Does the method protect low-count cells and resist simple reverse engineering attacks?

Primary metrics:

1. Fraction of true low-count cells directly inferable from released data
2. Vulnerability to differencing across related releases
3. Vulnerability to repeated-release attacks
4. Effective masking margin for sparse cells

### 4. Operational Feasibility

Question:
Can sites run the method reliably and can the coordinating center use the outputs without excessive complexity?

Primary metrics:

1. Runtime and memory burden
2. Failure rate across sites
3. Number of analyst decisions required
4. Fraction of cells retained for analysis
5. Reproducibility across repeated runs

### 5. Robustness

Question:
How well does the method hold up under realistic federated failure modes?

Primary metrics:

1. Performance under sparse-cell settings
2. Performance when only a subset of sites return data
3. Performance under alternative geographic granularities
4. Performance across common versus rare cohorts

## Experimental Design Families

### Experiment 1: Local Truth Versus Release

At each site, generate the same geographic summaries from the same underlying CLIF cohort under each privacy method.

Compare:

1. true local aggregate outputs
2. masked local aggregate outputs
3. demasked pooled outputs where applicable

Purpose:
This quantifies direct distortion introduced before pooling.

### Experiment 2: Pooled Recovery

For each population and each masking method, pool site returns centrally and compare the final pooled result against the pooled truth generated from the unmasked site aggregates.

Compare:

1. pooled counts
2. pooled rates
3. pooled subgroup summaries
4. pooled model coefficients

Purpose:
This is the main end-to-end test of whether the method supports valid federated inference.

### Experiment 3: Spatial Signal Preservation

For each population, evaluate whether the method preserves county-level scientific conclusions.

Examples:

1. county burden maps
2. county risk quartiles
3. high-burden hotspot identification
4. county-level exposure-outcome associations

Purpose:
This is critical because geographic utility is one of the central strengths of the proposed deterministic masking approach.

### Experiment 4: Sparse Cell Stress Test

Stratify all released cells by true count size and compare performance across:

1. 0 to 5
2. 6 to 10
3. 11 to 25
4. more than 25

Purpose:
This reveals whether a method only works in dense cells or remains usable in rare subgroups and uncommon counties.

### Experiment 5: Partial Site Participation

Repeat the pooled analysis under multiple site-return scenarios:

1. all sites
2. random 80% of sites
3. random 50% of sites
4. only large sites
5. only mixed large and small sites

Purpose:
This tests real-world federated resilience, especially for deterministic demasking workflows that depend on consistent key design.

### Experiment 6: Repeated Release Stability

Run the same site workflow multiple times on the same underlying truth.

Purpose:
This quantifies method stability. Deterministic masking should produce identical releases from identical inputs, while random perturbation methods should not.

## Population-Specific Aims

### Population 1: All Adult ICU Hospitalizations

Why include it:
This is the broad denominator cohort and provides the highest-volume, least sparse test bed.

Best use in experiments:

1. geographic fidelity of crude ICU burden
2. age-sex standardization
3. operational benchmarking

### Population 2: Sepsis

Why include it:
This is the main complex phenotype cohort and stresses multi-table derivation.

Best use in experiments:

1. pooled recovery of a clinically meaningful derived phenotype
2. preservation of geographic burden and disparity patterns
3. downstream regression or rate modeling

### Population 3: Cardiac Arrest Present On Admission

Why include it:
This is an acute diagnosis-based cohort with expected spatial sparsity and strong severity contrast.

Best use in experiments:

1. sparse-cell stress testing
2. hotspot agreement
3. low-count privacy evaluation

## Recommended Analysis Sequence

Before designing the final exported table schemas, we should lock the methodological sequence:

1. Build the three cohorts locally from CLIF
2. Generate a site-truth version of each downstream summary
3. Apply each privacy method to the same summaries
4. Pool returns centrally
5. Compare released or demasked outputs against the pooled truth
6. Repeat under sparse-cell and partial-site scenarios

## Primary Claim Structure

If the results support it, the paper can make the following claim:

Deterministic masking preserves geographic signal, pooled inference, and operational reproducibility better than suppression- or randomness-based approaches, while maintaining acceptable protection against direct recovery of low-count cells.

## Decision Rule For Superiority

The deterministic method should be considered superior if it:

1. matches or exceeds the privacy protection of comparator methods for low-count cells
2. yields lower geographic and statistical error in the pooled final analyses
3. retains more usable cells than suppression-heavy alternatives
4. produces stable and reproducible outputs across repeated runs
5. remains workable under realistic federated site-participation scenarios
