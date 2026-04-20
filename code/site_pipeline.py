from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Callable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "config.json"
KEYS_DIR = ROOT / "keys"

START_DATE = pd.Timestamp("2018-01-01", tz="UTC")
END_DATE = pd.Timestamp("2025-12-31 23:59:59", tz="UTC")
ADULT_AGE_YEARS = 18

OHCA_ICD10_PREFIXES = ("I46",)
OHCA_ICD9_PREFIXES = ("4275",)

COHORT_NAMES = (
    "all_icu_adult",
    "sepsis_ase_icu",
    "cardiac_arrest_poa_icu",
)
SUMMARY_FAMILIES = (
    "site_cohort_summary",
    "county_year_burden_summary",
    "county_year_age_sex_summary",
    "year_age_sex_race_ethnicity_summary",
)
COUNT_COLUMNS = {
    "site_cohort_summary": ["n_hospitalizations", "n_patients", "n_with_geo", "death_n", "prolonged_icu_los_n"],
    "county_year_burden_summary": ["hospitalizations", "deaths", "missing_county_hospitalizations"],
    "county_year_age_sex_summary": ["hospitalizations", "deaths"],
    "year_age_sex_race_ethnicity_summary": ["hospitalizations", "deaths"],
}
RATE_COLUMNS = {
    "site_cohort_summary": ["pct_with_geo", "mortality_pct", "prolonged_icu_los_pct"],
    "county_year_burden_summary": ["mortality_pct"],
    "county_year_age_sex_summary": ["mortality_pct"],
    "year_age_sex_race_ethnicity_summary": ["mortality_pct"],
}
RELEASE_LEVEL = {
    "site_cohort_summary": "site",
    "county_year_burden_summary": "county",
    "county_year_age_sex_summary": "county",
    "year_age_sex_race_ethnicity_summary": "demo",
}
KEY_FILE_BASENAME = {
    "site_cohort_summary": "key_site_cohort_summary",
    "county_year_burden_summary": "key_county_year",
    "county_year_age_sex_summary": "key_county_year_age_sex",
    "year_age_sex_race_ethnicity_summary": "key_year_age_sex_race_ethnicity",
}
KEY_JOIN_COLUMNS = {
    "site_cohort_summary": ["population_id"],
    "county_year_burden_summary": ["county_fips", "admit_year"],
    "county_year_age_sex_summary": ["county_fips", "admit_year", "age_band", "sex_group"],
    "year_age_sex_race_ethnicity_summary": ["admit_year", "age_band", "sex_group", "race_group", "ethnicity_group"],
}
COUNTY_FIPS_ALIASES = {
    "09003": "09110",
}
RANDOM_REPLICATES = ("rep1", "rep2", "rep3")
SUPPRESSION_THRESHOLD = 10
SUPPRESSION_LABEL = "<10"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("Missing config/config.json. Create it from config/config_template.json first.")
    with CONFIG_PATH.open() as handle:
        return json.load(handle)


def ensure_within_repo(path: Path) -> Path:
    resolved = path.resolve()
    root_resolved = ROOT.resolve()
    if not str(resolved).startswith(str(root_resolved) + "/") and resolved != root_resolved:
        raise ValueError(f"Path must stay within the repo: {resolved}")
    return resolved


def resolve_output_root(config: dict) -> Path:
    return ensure_within_repo(ROOT / "output")


def resolve_tables_path(config: dict) -> Path:
    tables_value = config.get("tables_path")
    if not tables_value:
        raise KeyError("Config must include 'tables_path'.")
    return Path(tables_value).expanduser().resolve()


def normalize_file_type(file_type: str) -> str:
    normalized = str(file_type).strip().lower()
    if normalized not in {"csv", "parquet"}:
        raise ValueError("This pipeline currently supports only csv and parquet inputs.")
    return normalized


def cohorts_dir(config: dict) -> Path:
    return resolve_output_root(config) / "intermediate" / "cohorts"


def logs_dir(config: dict) -> Path:
    return resolve_output_root(config) / "logs"


def exports_dir(config: dict, method_id: str) -> Path:
    return ensure_within_repo(resolve_output_root(config) / "final" / "site_exports" / method_id)


def final_tables_dir(config: dict) -> Path:
    return ensure_within_repo(resolve_output_root(config) / "final" / "tables")


def keys_dir() -> Path:
    return ensure_within_repo(KEYS_DIR)


def table_path(tables_path: Path, file_type: str, table_name: str) -> Path:
    return tables_path / f"clif_{table_name}.{file_type}"


def read_table(tables_path: Path, file_type: str, table_name: str) -> pd.DataFrame:
    path = table_path(tables_path, file_type, table_name)
    if not path.exists():
        raise FileNotFoundError(f"Missing required CLIF table: {path}")
    if file_type == "parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def as_utc_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def norm_code(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.upper()
        .str.replace(r"[^A-Z0-9]", "", regex=True)
        .str.strip()
    )


def normalize_county_fips(series: pd.Series) -> pd.Series:
    clean = (
        series.fillna("")
        .astype(str)
        .str.replace(r"[^0-9]", "", regex=True)
        .str.strip()
    )
    clean = clean.where(clean.str.len() == 5, other=pd.NA)
    clean = clean.replace(COUNTY_FIPS_ALIASES)
    return clean


def normalize_release_fips(series: pd.Series) -> pd.Series:
    clean = (
        series.fillna("")
        .astype(str)
        .str.replace(r"[^0-9]", "", regex=True)
        .str.zfill(5)
        .str[-5:]
    )
    clean = clean.replace(COUNTY_FIPS_ALIASES)
    return clean.where(clean != "00000", pd.NA)


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
    out[x.isin(["", "unknown", "declined", "refused", "unable to obtain"])] = "Unknown"
    non_hispanic = x.str.contains(r"\bnon[- ]?hispanic\b|\bnot[- ]?hispanic\b", regex=True)
    hispanic = x.str.contains(r"\bhispanic\b|\blatino\b", regex=True) & ~non_hispanic
    out[hispanic] = "Hispanic or Latino"
    out[non_hispanic] = "Not Hispanic or Latino"
    return out


def load_cohort(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    for col in ("admission_dttm", "discharge_dttm", "first_icu_in", "last_icu_out"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    return df


def build_all_icu_cohort(patient: pd.DataFrame, hospitalization: pd.DataFrame, adt: pd.DataFrame) -> pd.DataFrame:
    patient_min = patient.loc[:, [c for c in ["patient_id", "sex_category", "race_category", "ethnicity_category"] if c in patient.columns]].copy()
    patient_min["patient_id"] = patient_min["patient_id"].astype(str)

    hosp_cols = [
        "patient_id",
        "hospitalization_id",
        "admission_dttm",
        "discharge_dttm",
        "age_at_admission",
        "discharge_category",
        "zipcode_five_digit",
        "zipcode_nine_digit",
        "census_tract",
        "county_code",
        "state_code",
    ]
    hosp = hospitalization.loc[:, [c for c in hosp_cols if c in hospitalization.columns]].copy()
    hosp["patient_id"] = hosp["patient_id"].astype(str)
    hosp["hospitalization_id"] = hosp["hospitalization_id"].astype(str)
    hosp["admission_dttm"] = as_utc_datetime(hosp["admission_dttm"])
    hosp["discharge_dttm"] = as_utc_datetime(hosp["discharge_dttm"])
    hosp["age_at_admission"] = pd.to_numeric(hosp["age_at_admission"], errors="coerce")

    base = hosp.merge(patient_min, on="patient_id", how="left")
    base = base[
        base["admission_dttm"].notna()
        & (base["admission_dttm"] >= START_DATE)
        & (base["admission_dttm"] <= END_DATE)
        & (base["age_at_admission"] >= ADULT_AGE_YEARS)
    ].copy()

    adt_min = adt.loc[:, [c for c in ["hospitalization_id", "in_dttm", "out_dttm", "location_category", "location_type"] if c in adt.columns]].copy()
    adt_min["hospitalization_id"] = adt_min["hospitalization_id"].astype(str)
    adt_min["in_dttm"] = as_utc_datetime(adt_min["in_dttm"])
    adt_min["out_dttm"] = as_utc_datetime(adt_min["out_dttm"])
    adt_min["location_category"] = adt_min["location_category"].fillna("").astype(str).str.lower()

    icu_segments = adt_min[adt_min["location_category"].str.contains("icu", na=False)].copy()
    icu_bounds = (
        icu_segments.groupby("hospitalization_id", as_index=False)
        .agg(
            first_icu_in=("in_dttm", "min"),
            last_icu_out=("out_dttm", "max"),
            n_icu_segments=("hospitalization_id", "size"),
        )
    )
    icu_bounds["icu_los_hours"] = (icu_bounds["last_icu_out"] - icu_bounds["first_icu_in"]).dt.total_seconds() / 3600.0

    all_icu = base.merge(icu_bounds, on="hospitalization_id", how="inner")
    all_icu["admit_year"] = all_icu["admission_dttm"].dt.year
    all_icu["has_geo"] = (
        all_icu.get("county_code", pd.Series(index=all_icu.index)).notna()
        | all_icu.get("census_tract", pd.Series(index=all_icu.index)).notna()
        | all_icu.get("zipcode_five_digit", pd.Series(index=all_icu.index)).notna()
        | all_icu.get("zipcode_nine_digit", pd.Series(index=all_icu.index)).notna()
    )
    return all_icu.sort_values(["admission_dttm", "hospitalization_id"]).reset_index(drop=True)


def build_ohca_poa_cohort(all_icu: pd.DataFrame, hospital_diagnosis: pd.DataFrame) -> pd.DataFrame:
    dx_cols = ["hospitalization_id", "diagnosis_code", "diagnosis_code_format", "poa_present", "diagnosis_primary"]
    dx = hospital_diagnosis.loc[:, [c for c in dx_cols if c in hospital_diagnosis.columns]].copy()
    dx["hospitalization_id"] = dx["hospitalization_id"].astype(str)
    dx["diagnosis_code_clean"] = norm_code(dx["diagnosis_code"])
    dx["diagnosis_code_format"] = dx["diagnosis_code_format"].fillna("").astype(str).str.upper()
    dx["poa_present"] = pd.to_numeric(dx["poa_present"], errors="coerce").fillna(0).astype(int)

    is_ohca = (
        (
            dx["diagnosis_code_format"].str.contains("10", na=False)
            & dx["diagnosis_code_clean"].str.startswith(OHCA_ICD10_PREFIXES)
        )
        | (
            dx["diagnosis_code_format"].str.contains("9", na=False)
            & dx["diagnosis_code_clean"].str.startswith(OHCA_ICD9_PREFIXES)
        )
    )

    dx_ohca = dx[(dx["poa_present"] == 1) & is_ohca].copy()
    ohca_summary = (
        dx_ohca.groupby("hospitalization_id", as_index=False)
        .agg(
            cardiac_arrest_poa=("hospitalization_id", "size"),
            cardiac_arrest_codes_poa=("diagnosis_code_clean", lambda s: " | ".join(sorted(set(s)))),
        )
    )
    ohca_summary["cardiac_arrest_poa"] = 1

    return all_icu.merge(ohca_summary, on="hospitalization_id", how="inner").sort_values(
        ["admission_dttm", "hospitalization_id"]
    ).reset_index(drop=True)


def build_sepsis_cohort(all_icu: pd.DataFrame, tables_path: Path, file_type: str) -> pd.DataFrame:
    try:
        from clifpy.utils.ase import compute_ase
    except ImportError as exc:
        raise ImportError("clifpy is required for the sepsis cohort. Install clifpy to compute ASE.") from exc

    hosp_ids = all_icu["hospitalization_id"].astype(str).dropna().unique().tolist()
    ase_results = compute_ase(
        hospitalization_ids=hosp_ids,
        data_directory=str(tables_path),
        filetype=file_type,
        timezone="UTC",
        apply_rit=True,
        rit_only_hospital_onset=True,
        include_lactate=False,
        verbose=True,
    )

    ase = pd.DataFrame(ase_results).copy()
    if ase.empty:
        return all_icu.iloc[0:0].copy()

    ase["hospitalization_id"] = ase["hospitalization_id"].astype(str)
    if "sepsis_wo_lactate" in ase.columns:
        sepsis_flag = pd.to_numeric(ase["sepsis_wo_lactate"], errors="coerce").fillna(0).astype(int)
    else:
        sepsis_flag = pd.to_numeric(ase["sepsis"], errors="coerce").fillna(0).astype(int)
    ase = ase[sepsis_flag == 1].copy()

    onset_col = "ase_onset_w_lactate_dttm" if "ase_onset_w_lactate_dttm" in ase.columns else "blood_culture_dttm"
    if onset_col in ase.columns:
        ase[onset_col] = as_utc_datetime(ase[onset_col])

    sort_cols = [c for c in [onset_col, "episode_id", "bc_id"] if c in ase.columns]
    if sort_cols:
        ase = ase.sort_values(sort_cols)

    keep_cols = [c for c in [
        "hospitalization_id",
        "episode_id",
        "type",
        "presumed_infection",
        "sepsis",
        "sepsis_wo_lactate",
        "blood_culture_dttm",
        "ase_onset_w_lactate_dttm",
        "ase_first_criteria_w_lactate",
        "no_sepsis_reason",
    ] if c in ase.columns]
    ase_first = ase.loc[:, keep_cols].drop_duplicates(subset=["hospitalization_id"], keep="first")
    ase_first = ase_first.rename(
        columns={
            "type": "ase_onset_type",
            "blood_culture_dttm": "ase_blood_culture_dttm",
            "ase_onset_w_lactate_dttm": "ase_onset_dttm",
            "ase_first_criteria_w_lactate": "ase_first_criterion",
        }
    )

    return all_icu.merge(ase_first, on="hospitalization_id", how="inner").sort_values(
        ["admission_dttm", "hospitalization_id"]
    ).reset_index(drop=True)


def write_cohort_outputs(site_name: str, cohorts: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    for cohort_name, df in cohorts.items():
        cohort_path = output_dir / f"{cohort_name}_{site_name}.parquet"
        df.to_parquet(cohort_path, index=False)
        summary_rows.append(
            {
                "site_name": site_name,
                "cohort_name": cohort_name,
                "n_hospitalizations": int(df["hospitalization_id"].nunique()) if not df.empty else 0,
                "n_patients": int(df["patient_id"].nunique()) if ("patient_id" in df.columns and not df.empty) else 0,
                "n_with_geo": int(df["has_geo"].fillna(False).sum()) if "has_geo" in df.columns else None,
                "admission_start": df["admission_dttm"].min() if "admission_dttm" in df.columns and not df.empty else pd.NaT,
                "admission_end": df["admission_dttm"].max() if "admission_dttm" in df.columns and not df.empty else pd.NaT,
                "output_path": str(cohort_path),
            }
        )
    pd.DataFrame(summary_rows).to_csv(output_dir / f"cohort_summary_{site_name}.csv", index=False)


def remove_transient_logs(config: dict) -> None:
    log_root = logs_dir(config)
    if not log_root.exists():
        return
    for path in sorted(log_root.rglob("*"), reverse=True):
        if path.is_file() or path.is_symlink():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    log_root.rmdir()


def remove_intermediate_outputs(config: dict) -> None:
    intermediate_root = resolve_output_root(config) / "intermediate"
    if not intermediate_root.exists():
        return
    for path in sorted(intermediate_root.rglob("*"), reverse=True):
        if path.is_file() or path.is_symlink():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    intermediate_root.rmdir()


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
        out.get("discharge_category", pd.Series(index=out.index)).fillna("").astype(str).str.strip().str.lower().eq("expired").astype(int)
    )
    if "icu_los_hours" not in out.columns:
        out["icu_los_hours"] = ((out["last_icu_out"] - out["first_icu_in"]).dt.total_seconds() / 3600.0)
    out["prolonged_icu_los_flag"] = (pd.to_numeric(out["icu_los_hours"], errors="coerce") >= 168).fillna(False).astype(int)
    return out


def site_cohort_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame([{
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
        }])
    return pd.DataFrame([{
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
    }])


def county_year_burden_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[
            "site_name", "cohort_name", "county_fips", "admit_year", "hospitalizations", "deaths", "mortality_pct", "missing_county_hospitalizations"
        ])
    known = (
        df[df["county_fips"].notna()]
        .groupby(["site_name", "cohort_name", "county_fips", "admit_year"], as_index=False)
        .agg(hospitalizations=("hospitalization_id", "nunique"), deaths=("death_flag", "sum"))
    )
    known["mortality_pct"] = known["deaths"] / known["hospitalizations"]
    missing = (
        df.groupby(["site_name", "cohort_name", "admit_year"], as_index=False)
        .agg(missing_county_hospitalizations=("county_fips", lambda s: int(s.isna().sum())))
    )
    return known.merge(missing, on=["site_name", "cohort_name", "admit_year"], how="left")


def county_year_age_sex_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[
            "site_name", "cohort_name", "county_fips", "admit_year", "age_band", "sex_group", "hospitalizations", "deaths", "mortality_pct"
        ])
    out = (
        df[df["county_fips"].notna()]
        .groupby(["site_name", "cohort_name", "county_fips", "admit_year", "age_band", "sex_group"], as_index=False)
        .agg(hospitalizations=("hospitalization_id", "nunique"), deaths=("death_flag", "sum"))
    )
    out["mortality_pct"] = out["deaths"] / out["hospitalizations"]
    return out


def year_age_sex_race_ethnicity_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[
            "site_name", "cohort_name", "admit_year", "age_band", "sex_group", "race_group", "ethnicity_group", "hospitalizations", "deaths", "mortality_pct"
        ])
    out = (
        df.groupby(["site_name", "cohort_name", "admit_year", "age_band", "sex_group", "race_group", "ethnicity_group"], as_index=False)
        .agg(hospitalizations=("hospitalization_id", "nunique"), deaths=("death_flag", "sum"))
    )
    out["mortality_pct"] = out["deaths"] / out["hospitalizations"]
    return out


def normalize_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "cohort_name" in out.columns:
        out = out.rename(columns={"cohort_name": "population_id"})
    return out


def recompute_rates(family_name: str, df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if family_name == "site_cohort_summary":
        if {"n_with_geo", "n_hospitalizations"} <= set(out.columns):
            out["pct_with_geo"] = out["n_with_geo"] / out["n_hospitalizations"].replace({0: pd.NA})
        if {"death_n", "n_hospitalizations"} <= set(out.columns):
            out["mortality_pct"] = out["death_n"] / out["n_hospitalizations"].replace({0: pd.NA})
        if {"prolonged_icu_los_n", "n_hospitalizations"} <= set(out.columns):
            out["prolonged_icu_los_pct"] = out["prolonged_icu_los_n"] / out["n_hospitalizations"].replace({0: pd.NA})
    elif {"deaths", "hospitalizations"} <= set(out.columns):
        out["mortality_pct"] = out["deaths"] / out["hospitalizations"].replace({0: pd.NA})
    return out


def write_release_table(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def manifest_row(
    site_name: str,
    population_id: str,
    method_id: str,
    family_name: str,
    file_name: str,
    n_rows: int,
    release_level: str,
    replicate_id: str = "",
    mask_version: str = "",
    notes: str = "",
) -> dict:
    return {
        "site_name": site_name,
        "population_id": population_id,
        "method_id": method_id,
        "table_family": family_name,
        "file_name": file_name,
        "n_rows": int(n_rows),
        "release_level": release_level,
        "replicate_id": replicate_id,
        "mask_version": mask_version,
        "notes": notes,
    }


def suppression_mask(df: pd.DataFrame, cols: list[str], threshold: int, label: str) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            values = pd.to_numeric(out[col], errors="coerce")
            suppress_mask = (values >= 0) & (values < threshold)
            out[col] = out[col].astype("object")
            out.loc[suppress_mask, col] = label
    return out


def find_key_fragment(family_name: str) -> tuple[Path | None, str]:
    pattern = f"{KEY_FILE_BASENAME[family_name]}_Fragment_*.csv"
    matches = sorted(keys_dir().glob(pattern))
    if not matches:
        return None, ""
    key_path = matches[0]
    match = re.search(r"Fragment_([A-Za-z0-9]+)\.csv$", key_path.name)
    return key_path, (match.group(1) if match else "")


def apply_key_offsets(family_name: str, df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    key_path, fragment_id = find_key_fragment(family_name)
    if key_path is None:
        raise FileNotFoundError(
            f"Missing key fragment for {family_name}. Expected {KEY_FILE_BASENAME[family_name]}_Fragment_*.csv in {keys_dir()}."
        )
    out = df.copy()
    key_df = pd.read_csv(key_path)
    join_cols = KEY_JOIN_COLUMNS[family_name]
    for col in join_cols:
        if col in out.columns:
            out[col] = out[col].astype(str)
        if col in key_df.columns:
            key_df[col] = key_df[col].astype(str)
    if "county_fips" in join_cols:
        out["county_fips"] = normalize_release_fips(out["county_fips"])
        key_df["county_fips"] = normalize_release_fips(key_df["county_fips"])
    merged = out.merge(key_df, on=join_cols, how="left", validate="many_to_one")
    if merged["offset"].isna().any():
        missing = merged.loc[merged["offset"].isna(), join_cols].drop_duplicates()
        raise ValueError(
            f"Key fragment {key_path.name} did not cover all rows for {family_name}. Missing examples: {missing.head(10).to_dict(orient='records')}"
        )
    for col in [c for c in COUNT_COLUMNS[family_name] if c in merged.columns]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0).astype(int) + merged["offset"].astype(int)
    for col in RATE_COLUMNS.get(family_name, []):
        if col in merged.columns:
            merged[col] = pd.NA
    merged = merged.drop(columns=["offset"])
    return merged, {
        "notes": f"Deterministic offsets applied using {key_path.name}. Rates left blank for central recomputation.",
        "mask_version": f"Fragment_{fragment_id}" if fragment_id else key_path.stem,
    }


def apply_random_perturbation(family_name: str, df: pd.DataFrame, replicate_id: str) -> pd.DataFrame:
    out = df.copy()
    for col in [c for c in COUNT_COLUMNS[family_name] if c in out.columns]:
        values = pd.to_numeric(out[col], errors="coerce").fillna(0).astype(int)
        perturb = []
        for row_idx in range(len(values)):
            seed_key = f"{family_name}|{replicate_id}|{col}|{row_idx}"
            row_seed = int(hashlib.sha256(seed_key.encode("utf-8")).hexdigest()[:12], 16)
            perturb.append(random.Random(row_seed).randint(-3, 3))
        out[col] = (values + pd.Series(perturb, index=values.index)).clip(lower=0).astype(int)
    return recompute_rates(family_name, out)


def county_to_state(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "county_fips" not in out.columns:
        return out
    out["state_fips"] = out["county_fips"].astype(str).str[:2]
    return out.drop(columns=["county_fips"])


def build_release_tables_from_cohort(cohort_df: pd.DataFrame, site_name: str, cohort_name: str) -> dict[str, pd.DataFrame]:
    prepared = prepare_common_fields(cohort_df, site_name, cohort_name)
    family_outputs = {
        "site_cohort_summary": site_cohort_summary(prepared),
        "county_year_burden_summary": county_year_burden_summary(prepared),
        "county_year_age_sex_summary": county_year_age_sex_summary(prepared),
        "year_age_sex_race_ethnicity_summary": year_age_sex_race_ethnicity_summary(prepared),
    }
    family_outputs["site_cohort_summary"]["site_name"] = site_name
    family_outputs["site_cohort_summary"]["cohort_name"] = cohort_name
    return {family_name: normalize_summary(df) for family_name, df in family_outputs.items()}


def load_prepared_cohort_cache(config: dict) -> dict[str, pd.DataFrame]:
    site_name = str(config["site_name"])
    cohort_root = cohorts_dir(config)
    cache: dict[str, pd.DataFrame] = {}
    for cohort_name in COHORT_NAMES:
        cohort_path = cohort_root / f"{cohort_name}_{site_name}.parquet"
        if not cohort_path.exists():
            raise FileNotFoundError(f"Missing cohort file: {cohort_path}. Run cohorts first.")
        cache[cohort_name] = prepare_common_fields(load_cohort(cohort_path), site_name, cohort_name)
    return cache


def build_release_cache(config: dict) -> dict[str, dict[str, pd.DataFrame]]:
    site_name = str(config["site_name"])
    cohort_cache = load_prepared_cohort_cache(config)
    cache: dict[str, dict[str, pd.DataFrame]] = {}
    for cohort_name, cohort_df in cohort_cache.items():
        cache[cohort_name] = build_release_tables_from_cohort(cohort_df, site_name, cohort_name)
    return cache


def format_n_pct(n: int, denom: int) -> str:
    if denom <= 0:
        return "0 (0.0%)"
    return f"{int(n)} ({100.0 * float(n) / float(denom):.1f}%)"


def format_median_iqr(series: pd.Series) -> str:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return "NA"
    q1 = numeric.quantile(0.25)
    med = numeric.median()
    q3 = numeric.quantile(0.75)
    return f"{med:.1f} [{q1:.1f}, {q3:.1f}]"


def build_site_table1(prepared_cache: dict[str, pd.DataFrame]) -> pd.DataFrame:
    columns = list(COHORT_NAMES)
    rows: list[dict[str, str]] = []

    def add_row(characteristic: str, values: dict[str, str]) -> None:
        row = {"Characteristic": characteristic}
        for cohort_name in columns:
            row[cohort_name] = values.get(cohort_name, "")
        rows.append(row)

    for cohort_name, df in prepared_cache.items():
        n_hosp = int(df["hospitalization_id"].nunique())
        n_pat = int(df["patient_id"].nunique())
        values = {
            "Hospitalizations, n": str(n_hosp),
            "Patients, n": str(n_pat),
            "Age at admission, median [IQR]": format_median_iqr(df["age_at_admission"]),
            "ICU LOS hours, median [IQR]": format_median_iqr(df["icu_los_hours"]),
            "In-hospital death": format_n_pct(int(df["death_flag"].sum()), n_hosp),
            "Has county FIPS": format_n_pct(int(df["county_fips"].notna().sum()), n_hosp),
            "Female": format_n_pct(int((df["sex_group"] == "Female").sum()), n_hosp),
            "Male": format_n_pct(int((df["sex_group"] == "Male").sum()), n_hosp),
            "Other/Unknown sex": format_n_pct(int((df["sex_group"] == "Other/Unknown").sum()), n_hosp),
            "White": format_n_pct(int((df["race_group"] == "White").sum()), n_hosp),
            "Black": format_n_pct(int((df["race_group"] == "Black").sum()), n_hosp),
            "Asian": format_n_pct(int((df["race_group"] == "Asian").sum()), n_hosp),
            "AIAN": format_n_pct(int((df["race_group"] == "AIAN").sum()), n_hosp),
            "NHPI": format_n_pct(int((df["race_group"] == "NHPI").sum()), n_hosp),
            "Other/Unknown race": format_n_pct(int((df["race_group"] == "Other/Unknown").sum()), n_hosp),
            "Hispanic or Latino": format_n_pct(int((df["ethnicity_group"] == "Hispanic or Latino").sum()), n_hosp),
            "Not Hispanic or Latino": format_n_pct(int((df["ethnicity_group"] == "Not Hispanic or Latino").sum()), n_hosp),
            "Unknown ethnicity": format_n_pct(int((df["ethnicity_group"] == "Unknown").sum()), n_hosp),
        }
        for characteristic, value in values.items():
            existing = next((r for r in rows if r["Characteristic"] == characteristic), None)
            if existing is None:
                add_row(characteristic, {cohort_name: value})
            else:
                existing[cohort_name] = value

    table = pd.DataFrame(rows, columns=["Characteristic", *columns])
    return table


def write_table1_outputs(config: dict, table1: pd.DataFrame) -> None:
    site_name = str(config["site_name"])
    out_dir = final_tables_dir(config)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"table1_site_summary_{site_name}.csv"
    md_path = out_dir / f"table1_site_summary_{site_name}.md"
    table1.to_csv(csv_path, index=False)
    headers = list(table1.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in table1.iterrows():
        vals = [str("" if pd.isna(v) else v) for v in row.tolist()]
        lines.append("| " + " | ".join(vals) + " |")
    md_path.write_text("\n".join(lines) + "\n")


def run_release(
    config: dict,
    summary_cache: dict[str, dict[str, pd.DataFrame]],
    method_id: str,
    transform: Callable[[str, pd.DataFrame, str], tuple[pd.DataFrame, dict]],
    replicate_ids: tuple[str, ...] = ("",),
    families: tuple[str, ...] = SUMMARY_FAMILIES,
) -> None:
    site_name = str(config["site_name"])
    out_dir = exports_dir(config, method_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale_csv in out_dir.glob("*.csv"):
        stale_csv.unlink()
    manifest = []
    for cohort_name in COHORT_NAMES:
        for family_name in families:
            summary_df = summary_cache[cohort_name][family_name]
            for replicate_id in replicate_ids:
                released_df, meta = transform(family_name, summary_df.copy(), replicate_id)
                suffix = f"_{replicate_id}" if replicate_id else ""
                file_name = f"{family_name}_{method_id}_{cohort_name}_{site_name}{suffix}.csv"
                write_release_table(released_df, out_dir / file_name)
                manifest.append(
                    manifest_row(
                        site_name=site_name,
                        population_id=cohort_name,
                        method_id=method_id,
                        family_name=family_name,
                        file_name=file_name,
                        n_rows=len(released_df),
                        release_level=meta.get("release_level", RELEASE_LEVEL[family_name]),
                        replicate_id=replicate_id,
                        mask_version=meta.get("mask_version", ""),
                        notes=meta.get("notes", ""),
                    )
                )
    pd.DataFrame(manifest).to_csv(out_dir / f"site_export_manifest_{site_name}.csv", index=False)
    print(f"Created {method_id} release package in {out_dir}")


def run_cohorts(config: dict) -> None:
    site_name = str(config["site_name"])
    tables_path = resolve_tables_path(config)
    file_type = normalize_file_type(config["file_type"])
    output_dir = cohorts_dir(config)

    patient = read_table(tables_path, file_type, "patient")
    hospitalization = read_table(tables_path, file_type, "hospitalization")
    adt = read_table(tables_path, file_type, "adt")
    hospital_diagnosis = read_table(tables_path, file_type, "hospital_diagnosis")

    all_icu = build_all_icu_cohort(patient, hospitalization, adt)
    sepsis = build_sepsis_cohort(all_icu, tables_path, file_type)
    ohca = build_ohca_poa_cohort(all_icu, hospital_diagnosis)
    write_cohort_outputs(
        site_name=site_name,
        output_dir=output_dir,
        cohorts={
            "all_icu_adult": all_icu,
            "sepsis_ase_icu": sepsis,
            "cardiac_arrest_poa_icu": ohca,
        },
    )
    remove_transient_logs(config)
    print("Cohort identification complete.")


def run_deterministic_release(config: dict, summary_cache: dict[str, dict[str, pd.DataFrame]]) -> None:
    keyed_families = tuple(family for family in SUMMARY_FAMILIES if find_key_fragment(family)[0] is not None)
    if not keyed_families:
        raise FileNotFoundError("No deterministic key fragments found in keys/.")

    def transform(family_name: str, df: pd.DataFrame, replicate_id: str) -> tuple[pd.DataFrame, dict]:
        return apply_key_offsets(family_name, df)

    print(f"Using deterministic key fragments for: {', '.join(keyed_families)}")
    run_release(config, summary_cache, "det_offset", transform, families=keyed_families)


def run_suppression_release(config: dict, summary_cache: dict[str, dict[str, pd.DataFrame]]) -> None:
    def transform(family_name: str, df: pd.DataFrame, replicate_id: str) -> tuple[pd.DataFrame, dict]:
        released = suppression_mask(df, COUNT_COLUMNS[family_name], SUPPRESSION_THRESHOLD, SUPPRESSION_LABEL)
        for col in RATE_COLUMNS.get(family_name, []):
            if col in released.columns:
                released[col] = pd.NA
        return released, {
            "notes": f"Count cells below {SUPPRESSION_THRESHOLD} labeled as {SUPPRESSION_LABEL}; rates blanked for suppressed table release.",
        }

    run_release(config, summary_cache, "suppress_lt10", transform)


def run_random_release(config: dict, summary_cache: dict[str, dict[str, pd.DataFrame]]) -> None:
    def transform(family_name: str, df: pd.DataFrame, replicate_id: str) -> tuple[pd.DataFrame, dict]:
        return apply_random_perturbation(family_name, df, replicate_id), {
            "notes": "Independent bounded integer perturbation applied to count columns; rates recomputed from perturbed counts.",
        }

    run_release(config, summary_cache, "rand_unif_3", transform, replicate_ids=RANDOM_REPLICATES)


def run_state_coarsened_release(config: dict, summary_cache: dict[str, dict[str, pd.DataFrame]]) -> None:
    def transform(family_name: str, df: pd.DataFrame, replicate_id: str) -> tuple[pd.DataFrame, dict]:
        if family_name in {"site_cohort_summary", "year_age_sex_race_ethnicity_summary"}:
            released = df.copy()
            release_level = "site" if family_name == "site_cohort_summary" else "demo"
            note_prefix = "Non-geographic summary released unchanged before small-cell suppression for state-coarsened comparator."
        else:
            state_df = county_to_state(df)
            group_cols = [c for c in state_df.columns if c not in {"hospitalizations", "deaths", "missing_county_hospitalizations", "mortality_pct"}]
            agg_map = {col: "sum" for col in ["hospitalizations", "deaths", "missing_county_hospitalizations"] if col in state_df.columns}
            released = state_df.groupby(group_cols, as_index=False).agg(agg_map)
            released = recompute_rates(family_name, released)
            release_level = "state"
            note_prefix = "County summaries aggregated to state_fips before small-cell suppression."
        released = suppression_mask(released, COUNT_COLUMNS[family_name], SUPPRESSION_THRESHOLD, SUPPRESSION_LABEL)
        for col in RATE_COLUMNS.get(family_name, []):
            if col in released.columns:
                released[col] = pd.NA
        return released, {
            "release_level": release_level,
            "notes": f"{note_prefix} Count cells below {SUPPRESSION_THRESHOLD} labeled as {SUPPRESSION_LABEL}; rates blanked after suppression.",
        }

    run_release(config, summary_cache, "state_coarsen", transform)


def run_releases(config: dict, methods: list[str]) -> None:
    summary_cache = build_release_cache(config)
    if "det_offset" in methods:
        run_deterministic_release(config, summary_cache)
    if "suppress_lt10" in methods:
        run_suppression_release(config, summary_cache)
    if "rand_unif_3" in methods:
        run_random_release(config, summary_cache)
    if "state_coarsen" in methods:
        run_state_coarsened_release(config, summary_cache)
    remove_intermediate_outputs(config)


def run_site_table1(config: dict) -> None:
    prepared_cache = load_prepared_cohort_cache(config)
    table1 = build_site_table1(prepared_cache)
    write_table1_outputs(config, table1)
    print(f"Created site Table 1 in {final_tables_dir(config)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Single-entry CLIF deterministic masking site pipeline.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("cohorts", help="Build cohort parquet files.")
    subparsers.add_parser("table1", help="Build the site-level Table 1 summary from cohort files.")

    releases = subparsers.add_parser("releases", help="Build one or more release packages.")
    releases.add_argument(
        "--methods",
        nargs="+",
        choices=["det_offset", "suppress_lt10", "rand_unif_3", "state_coarsen"],
        default=["det_offset", "suppress_lt10", "rand_unif_3", "state_coarsen"],
        help="Release methods to generate.",
    )

    all_cmd = subparsers.add_parser("all", help="Run cohorts and build release packages.")
    all_cmd.add_argument(
        "--methods",
        nargs="+",
        choices=["det_offset", "suppress_lt10", "rand_unif_3", "state_coarsen"],
        default=["det_offset", "suppress_lt10", "rand_unif_3", "state_coarsen"],
        help="Release methods to generate.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    command = args.command or "all"
    config = load_config()

    if command == "cohorts":
        run_cohorts(config)
    elif command == "table1":
        run_site_table1(config)
    elif command == "releases":
        run_releases(config, args.methods)
    elif command == "all":
        run_cohorts(config)
        run_site_table1(config)
        run_releases(config, args.methods)
    else:
        parser.error(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
