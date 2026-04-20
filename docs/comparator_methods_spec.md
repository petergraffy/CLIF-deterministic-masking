# Comparator Methods Specification

## Overview

This document fixes the exact comparator methods for the deterministic masking validation study. Each comparator must operate on the same site-level truth summaries so that performance differences reflect the release method rather than different upstream analytics.

The methods are intentionally chosen to represent common privacy-preserving strategies for federated aggregate release.

## Method 1: Deterministic Offset Masking

### Definition

Each released cell is masked by adding a deterministic positive integer offset defined by an external site-specific key file. The key is indexed to the exact dimensions of the released table. The same offset is applied to all count columns within the same cell. Central pooled demasking is performed after masked outputs are received.

### Implementation Features

1. site-specific external key file
2. one offset value per released cell
3. same offset applied to all count columns within that cell
4. no randomness at release time
5. central demasking only after pooling

### Intended Strengths

1. exact reproducibility
2. high pooled recoverability
3. retention of sparse cells without direct suppression
4. compatibility with geographic releases

### Key Risks

1. poor key design could permit differencing attacks
2. complex coordination may be required for key management
3. performance depends on table dimensions being fixed in advance

## Method 2: Small-Cell Suppression

### Definition

All cells with counts below a fixed threshold are suppressed before release. To reduce back-calculation, complementary suppression is also applied when necessary.

### Fixed Parameters

1. primary suppression threshold: less than 10
2. complementary suppression: applied whenever a suppressed cell could be solved exactly from row or column totals

### Intended Strengths

1. familiar to many clinical data-sharing settings
2. simple to explain
3. direct protection for small cells

### Expected Weaknesses

1. major loss of analyzable data in sparse geographic tables
2. distortion of subgroup and county comparisons
3. difficult pooled inference when many cells are missing

## Method 3: Random Cell Perturbation

### Definition

Each released cell count is perturbed independently by adding a random draw from a zero-centered bounded discrete distribution. Negative results are truncated at zero.

### Fixed Parameters

1. perturbation distribution: discrete uniform from minus 3 to plus 3
2. post-perturbation truncation floor: 0
3. independent perturbation by cell

### Intended Strengths

1. easy to implement
2. preserves table completeness
3. provides a familiar stochastic masking baseline

### Expected Weaknesses

1. release instability across repeated runs
2. pooled estimates remain biased or noisy
3. weak performance for sparse or rare-event cells

## Method 4: Geographic Coarsening

### Definition

Release data only at a coarser geography instead of county level. The default comparator will aggregate county-based truth summaries to the state level before release.

### Fixed Parameters

1. coarsening target: state level
2. no additional masking beyond geographic aggregation in the primary implementation

### Intended Strengths

1. reduces sparsity
2. lowers direct small-cell risk in many settings
3. operationally simple

### Expected Weaknesses

1. discards county-level scientific signal
2. cannot support the main geographic use case of the study
3. may hide clinically meaningful spatial heterogeneity

## Standardized Comparison Rules

To make results directly comparable, all methods will follow these rules.

1. All methods operate on the same site-truth summary tables.
2. All methods are applied after cohort construction and truth-table derivation.
3. Pooled comparisons are always made against pooled truth.
4. Random methods are repeated multiple times.
5. Deterministic methods are evaluated for exact reproducibility.

## Planned Primary Comparisons

The primary pairwise comparisons are:

1. deterministic masking versus small-cell suppression
2. deterministic masking versus random perturbation
3. deterministic masking versus geographic coarsening

## Planned Sensitivity Analyses

Sensitivity analyses should vary a small number of parameters to check robustness.

### Suppression Sensitivity

1. threshold less than 6
2. threshold less than 10

### Random Perturbation Sensitivity

1. discrete uniform from minus 1 to plus 1
2. discrete uniform from minus 3 to plus 3
3. discrete uniform from minus 5 to plus 5

### Geographic Coarsening Sensitivity

1. county
2. state
3. multistate region if needed

### Deterministic Masking Sensitivity

1. alternative offset magnitude ranges
2. alternative table-key dimensionality
3. alternative demasking assumptions under partial site return

## Default Superiority Standard

Deterministic masking will be favored if it provides:

1. better pooled recovery than suppression and random perturbation
2. better county-level signal preservation than coarsening
3. better stability than random perturbation
4. more analyzable retained data than suppression
5. acceptable privacy behavior compared with all comparator methods
