## Output Directory

This directory holds site-generated deliverables.

## What Sites Should Keep

After a completed run, the important deliverables are in [output/final](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/output/final).

That folder should contain:

- `site_exports/`
- `tables/`

## Upload Instruction

Sites should upload the entire [output/final](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/output/final) folder to the project Box location provided by the coordinating center.

Do not upload:

- local CLIF source tables
- local config files
- transient logs
- intermediate cohort files

## Current Behavior

The site pipeline now removes `output/intermediate` after release generation is complete, and transient logs are also cleaned up automatically.
