from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "config.json"
COHORT_NAMES = (
    "all_icu_adult",
    "sepsis_ase_icu",
    "cardiac_arrest_poa_icu",
)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "Missing config/config.json. Create it from config/config_template.json first."
        )
    with CONFIG_PATH.open() as handle:
        return json.load(handle)


def resolve_output_root(config: dict) -> Path:
    return (ROOT / config.get("output_dir", "output")).resolve()


def cohorts_dir(config: dict) -> Path:
    return resolve_output_root(config) / "intermediate" / "cohorts"


def summaries_dir(config: dict) -> Path:
    return resolve_output_root(config) / "intermediate" / "shared_summaries"


def normalize_county_fips(series: pd.Series) -> pd.Series:
    clean = (
        series.fillna("")
        .astype(str)
        .str.replace(r"[^0-9]", "", regex=True)
        .str.strip()
    )
    clean = clean.where(clean.str.len() == 5, other=pd.NA)
    return clean


def age_band(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return pd.cut(
        numeric,
        bins=[18, 40, 65, 75, float("inf")],
        right=False,
        labels=["18-39", "40-64", "65-74", "75+"],
    ).astype("object").fillna("Unknown")


def harmonize_sex(series: pd.Series) -> pd.Series:
    x = series.fillna("").astype(str).str.strip().str.lower()
    out = pd.Series("Other/Unknown", index=series.index, dtype="object")
    out[x.isin(["female", "f"])] = "Female"
    out[x.isin(["male", "m"])] = "Male"
    return out


def harmonize_race(series: pd.Series) -> pd.Series:
    x = series.fillna("").astype(str).str.strip().str.lower()
    out = pd.Series("Other/Unknown", index=series.index, dtype="object")
    out[x.str.contains("american indian|alaska native|native american|aian", regex=True)] = "AIAN"
    out[x.str.contains("asian", regex=True)] = "Asian"
    out[x.str.contains("black|african", regex=True)] = "Black"
    out[x.str.contains("hawaiian|pacific", regex=True)] = "NHPI"
    out[x.str.contains("white", regex=True)] = "White"
    return out


def harmonize_ethnicity(series: pd.Series) -> pd.Series:
    x = series.fillna("").astype(str).str.strip().str.lower()
    out = pd.Series("Not Hispanic or Latino", index=series.index, dtype="object")
    out[x.str.contains("hispanic|latino", regex=True)] = "Hispanic or Latino"
    out[x.isin(["", "unknown", "declined", "refused", "unable to obtain"])] = "Unknown"
    return out


def load_cohort(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if "admission_dttm" in df.columns:
        df["admission_dttm"] = pd.to_datetime(df["admission_dttm"], utc=True, errors="coerce")
    if "discharge_dttm" in df.columns:
        df["discharge_dttm"] = pd.to_datetime(df["discharge_dttm"], utc=True, errors="coerce")
    if "first_icu_in" in df.columns:
        df["first_icu_in"] = pd.to_datetime(df["first_icu_in"], utc=True, errors="coerce")
    if "last_icu_out" in df.columns:
        df["last_icu_out"] = pd.to_datetime(df["last_icu_out"], utc=True, errors="coerce")
    return df


def prepare_common_fields(df: pd.DataFrame, site_name: str, cohort_name: str) -> pd.DataFrame:
    out = df.copy()
    out["site_name"] = site_name
    out["cohort_name"] = cohort_name
    out["patient_id"] = out["patient_id"].astype(str)
    out["hospitalization_id"] = out["hospitalization_id"].astype(str)
    out["admit_year"] = out["admission_dttm"].dt.year
    out["county_fips"] = normalize_county_fips(out.get("county_code", pd.Series(index=out.index)))
    out["age_band"] = age_band(out.get("age_at_admission", pd.Series(index=out.index)))
    out["sex_group"] = harmonize_sex(out.get("sex_category", pd.Series(index=out.index)))
    out["race_group"] = harmonize_race(out.get("race_category", pd.Series(index=out.index)))
    out["ethnicity_group"] = harmonize_ethnicity(out.get("ethnicity_category", pd.Series(index=out.index)))
    out["death_flag"] = (
        out.get("discharge_category", pd.Series(index=out.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("expired")
        .astype(int)
    )
    if "icu_los_hours" not in out.columns:
        out["icu_los_hours"] = (
            (out["last_icu_out"] - out["first_icu_in"]).dt.total_seconds() / 3600.0
        )
    out["prolonged_icu_los_flag"] = (pd.to_numeric(out["icu_los_hours"], errors="coerce") >= 168).fillna(False).astype(int)
    return out


def site_cohort_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            [
                {
                    "site_name": None,
                    "cohort_name": None,
                    "n_hospitalizations": 0,
                    "n_patients": 0,
                    "n_with_geo": 0,
                    "pct_with_geo": None,
                    "admission_year_min": None,
                    "admission_year_max": None,
                    "death_n": 0,
                    "mortality_pct": None,
                    "icu_los_hours_median": None,
                    "icu_los_hours_q3": None,
                    "prolonged_icu_los_n": 0,
                    "prolonged_icu_los_pct": None,
                }
            ]
        )
    return pd.DataFrame(
        [
            {
                "site_name": df["site_name"].iloc[0],
                "cohort_name": df["cohort_name"].iloc[0],
                "n_hospitalizations": int(df["hospitalization_id"].nunique()),
                "n_patients": int(df["patient_id"].nunique()),
                "n_with_geo": int(df["county_fips"].notna().sum()),
                "pct_with_geo": float(df["county_fips"].notna().mean()) if len(df) else None,
                "admission_year_min": int(df["admit_year"].min()) if df["admit_year"].notna().any() else None,
                "admission_year_max": int(df["admit_year"].max()) if df["admit_year"].notna().any() else None,
                "death_n": int(df["death_flag"].sum()),
                "mortality_pct": float(df["death_flag"].mean()) if len(df) else None,
                "icu_los_hours_median": float(pd.to_numeric(df["icu_los_hours"], errors="coerce").median()),
                "icu_los_hours_q3": float(pd.to_numeric(df["icu_los_hours"], errors="coerce").quantile(0.75)),
                "prolonged_icu_los_n": int(df["prolonged_icu_los_flag"].sum()),
                "prolonged_icu_los_pct": float(df["prolonged_icu_los_flag"].mean()) if len(df) else None,
            }
        ]
    )


def county_year_burden_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "site_name",
                "cohort_name",
                "county_fips",
                "admit_year",
                "hospitalizations",
                "deaths",
                "mortality_pct",
                "missing_county_hospitalizations",
            ]
        )
    known = (
        df[df["county_fips"].notna()]
        .groupby(["site_name", "cohort_name", "county_fips", "admit_year"], as_index=False)
        .agg(
            hospitalizations=("hospitalization_id", "nunique"),
            deaths=("death_flag", "sum"),
        )
    )
    known["mortality_pct"] = known["deaths"] / known["hospitalizations"]

    missing = (
        df.groupby(["site_name", "cohort_name", "admit_year"], as_index=False)
        .agg(
            missing_county_hospitalizations=("county_fips", lambda s: int(s.isna().sum())),
        )
    )
    if known.empty:
        return pd.DataFrame(
            columns=[
                "site_name",
                "cohort_name",
                "county_fips",
                "admit_year",
                "hospitalizations",
                "deaths",
                "mortality_pct",
                "missing_county_hospitalizations",
            ]
        )
    return known.merge(missing, on=["site_name", "cohort_name", "admit_year"], how="left")


def county_year_age_sex_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "site_name",
                "cohort_name",
                "county_fips",
                "admit_year",
                "age_band",
                "sex_group",
                "hospitalizations",
                "deaths",
                "mortality_pct",
            ]
        )
    out = df[df["county_fips"].notna()].groupby(
        ["site_name", "cohort_name", "county_fips", "admit_year", "age_band", "sex_group"],
        as_index=False,
    ).agg(
        hospitalizations=("hospitalization_id", "nunique"),
        deaths=("death_flag", "sum"),
    )
    out["mortality_pct"] = out["deaths"] / out["hospitalizations"]
    return out


def year_age_sex_race_ethnicity_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "site_name",
                "cohort_name",
                "admit_year",
                "age_band",
                "sex_group",
                "race_group",
                "ethnicity_group",
                "hospitalizations",
                "deaths",
                "mortality_pct",
            ]
        )
    out = df.groupby(
        ["site_name", "cohort_name", "admit_year", "age_band", "sex_group", "race_group", "ethnicity_group"],
        as_index=False,
    ).agg(
        hospitalizations=("hospitalization_id", "nunique"),
        deaths=("death_flag", "sum"),
    )
    out["mortality_pct"] = out["deaths"] / out["hospitalizations"]
    return out


def write_summary(summary_df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_parquet(output_path, index=False)
    summary_df.to_csv(output_path.with_suffix(".csv"), index=False)


def main() -> None:
    config = load_config()
    site_name = str(config["site_name"])
    cohort_dir = cohorts_dir(config)
    summary_root = summaries_dir(config)
    summary_root.mkdir(parents=True, exist_ok=True)

    manifest_rows = []

    for cohort_name in COHORT_NAMES:
        cohort_path = cohort_dir / f"{cohort_name}_{site_name}.parquet"
        if not cohort_path.exists():
            raise FileNotFoundError(
                f"Missing cohort file: {cohort_path}. Run code/01_cohort_identification.py first."
            )

        cohort_df = prepare_common_fields(load_cohort(cohort_path), site_name, cohort_name)
        family_outputs = {
            "site_cohort_summary": site_cohort_summary(cohort_df),
            "county_year_burden_summary": county_year_burden_summary(cohort_df),
            "county_year_age_sex_summary": county_year_age_sex_summary(cohort_df),
            "year_age_sex_race_ethnicity_summary": year_age_sex_race_ethnicity_summary(cohort_df),
        }

        family_outputs["site_cohort_summary"]["site_name"] = site_name
        family_outputs["site_cohort_summary"]["cohort_name"] = cohort_name

        for family_name, family_df in family_outputs.items():
            out_path = summary_root / f"{family_name}_{cohort_name}_{site_name}.parquet"
            write_summary(family_df, out_path)
            manifest_rows.append(
                {
                    "site_name": site_name,
                    "cohort_name": cohort_name,
                    "summary_family": family_name,
                    "n_rows": int(len(family_df)),
                    "parquet_path": str(out_path),
                    "csv_path": str(out_path.with_suffix(".csv")),
                }
            )

    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(summary_root / f"shared_summary_manifest_{site_name}.csv", index=False)
    print("Shared downstream summaries created.")
    print(f"Manifest: {summary_root / f'shared_summary_manifest_{site_name}.csv'}")


if __name__ == "__main__":
    main()
