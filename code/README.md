## Site Workflow

Sites should run the single entrypoint script:

```bash
./.venv/bin/python code/site_pipeline.py all
```

That full run does three things:

1. builds the three project cohorts
2. creates a site-level Table 1 summary
3. creates all four site export packages in `output/final/site_exports`

## Before You Start

1. Create `config/config.json` from [config/config_template.json](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/config/config_template.json)
2. Point `tables_path` or `clif_dir` to your local CLIF tables
3. Set `file_type` to `parquet` or `csv`
4. Keep `output_dir` repo-relative, usually `output`

The pipeline refuses to write outside the repository.

## Environment Setup

Recommended local environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas pyarrow clifpy tabulate
```

`clifpy` is required because the sepsis cohort uses the Adult Sepsis Event workflow.

## Deterministic Key Fragments

The deterministic release method requires external key fragments downloaded from the masking website or web app managed by the coordinating center.

Download the fragment CSVs for your site and place them in [keys](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/keys).

The pipeline expects these filename patterns:

- `key_county_year_Fragment_*.csv`
- `key_county_year_age_sex_Fragment_*.csv`
- `key_year_age_sex_race_ethnicity_Fragment_*.csv`

Examples:

- `key_county_year_Fragment_A.csv`
- `key_county_year_age_sex_Fragment_B.csv`
- `key_year_age_sex_race_ethnicity_Fragment_A.csv`

The wildcard suffix can differ by site. The code discovers the fragment automatically as long as the filename matches the pattern.

## Website Download Steps

Use the masking website as follows:

1. open the deterministic masking key website supplied by the coordinating center
2. select this project’s configured key sets
3. select your site
4. download the returned fragment CSV files
5. move those CSV files into the local [keys](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/keys) folder
6. confirm the folder now contains the three fragment families listed above

Do not rename the files beyond the website’s default fragment naming convention unless the names still match the required patterns.

## Run Options

Full run:

```bash
./.venv/bin/python code/site_pipeline.py all
```

Cohorts only:

```bash
./.venv/bin/python code/site_pipeline.py cohorts
```

Table 1 only:

```bash
./.venv/bin/python code/site_pipeline.py table1
```

Releases only:

```bash
./.venv/bin/python code/site_pipeline.py releases
```

Selected release methods only:

```bash
./.venv/bin/python code/site_pipeline.py releases --methods det_offset suppress_lt10
./.venv/bin/python code/site_pipeline.py releases --methods rand_unif_3 state_coarsen
```

## Release Methods

Supported method ids:

- `det_offset`
- `suppress_lt10`
- `rand_unif_3`
- `state_coarsen`

`det_offset` requires the downloaded key fragments. The other three methods do not.

## Final Outputs

After a full run, the main deliverables are:

- cohort files in [output/intermediate/cohorts](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/output/intermediate/cohorts)
- site Table 1 files in [output/final/tables](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/output/final/tables)
- site export packages in [output/final/site_exports](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/output/final/site_exports)

The code removes transient logs after cohorting, and it does not retain shared-summary export files as part of the finalized site package.

## Troubleshooting

- If `det_offset` fails, check that all three fragment files are in `keys/`
- If the sepsis cohort fails, confirm `clifpy` is installed in your active environment
- If the script complains about paths, make sure `output_dir` is repo-relative and `tables_path` points to the CLIF source tables
