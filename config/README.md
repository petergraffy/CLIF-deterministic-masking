## Configuration

1. Rename  `config_template.json` to `config.json`.
2. Update the `config.json` with site-specific settings.

Recommended fields for this repository:

1. `site_name`: short site identifier used in output file names
2. `repo`: absolute path to this repository
3. `tables_path`: absolute path to the CLIF tables directory
4. `file_type`: `parquet` or `csv`

The current code writes outputs to the repository's standard [output](/Users/saborpete/Desktop/Peter/Postdoc/CLIF-deterministic-masking/output) folder automatically, so no output path needs to be configured.

Note: the `.gitignore` file in this directory ensures that the information in the config file is not pushed to github remote repository. 
