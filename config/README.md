## Configuration

1. Rename  `config_template.json` to `config.json`.
2. Update the `config.json` with site-specific settings.

Recommended fields for this repository:

1. `site_name`: short site identifier used in output file names
2. `repo`: absolute path to this repository
3. `tables_path`: absolute path to the CLIF tables directory
4. `clif_dir`: optional alias for `tables_path` used by some other local repos
5. `file_type`: `parquet` or `csv`
6. `output_dir`: output root inside this repo, usually `output`
7. `site_timezone`: local site timezone for reference metadata

The current code will use `tables_path` if present, otherwise it will fall back to `clif_dir`.

Note: the `.gitignore` file in this directory ensures that the information in the config file is not pushed to github remote repository. 
