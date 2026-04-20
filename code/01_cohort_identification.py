from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "config.json"

START_DATE = pd.Timestamp("2018-01-01", tz="UTC")
END_DATE = pd.Timestamp("2025-12-31 23:59:59", tz="UTC")
ADULT_AGE_YEARS = 18

# This is intentionally labeled as a POA proxy cohort.
# CLIF core tables support diagnosis-present-on-admission, not verified arrest location.
OHCA_ICD10_PREFIXES = ("I46",)
OHCA_ICD9_PREFIXES = ("4275",)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "Missing config/config.json. Create it from config/config_template.json first."
        )
    with CONFIG_PATH.open() as handle:
        return json.load(handle)


def resolve_tables_path(config: dict) -> Path:
    tables_value = config.get("tables_path") or config.get("clif_dir")
    if not tables_value:
        raise KeyError("Config must include either 'tables_path' or 'clif_dir'.")
    return Path(tables_value).expanduser().resolve()


def resolve_output_dir(config: dict) -> Path:
    output_root = config.get("output_dir", "output")
    return (ROOT / output_root / "intermediate" / "cohorts").resolve()


def normalize_file_type(file_type: str) -> str:
    normalized = str(file_type).strip().lower()
    if normalized not in {"csv", "parquet"}:
        raise ValueError("This script currently supports only csv and parquet inputs.")
    return normalized


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


def build_all_icu_cohort(
    patient: pd.DataFrame,
    hospitalization: pd.DataFrame,
    adt: pd.DataFrame,
) -> pd.DataFrame:
    patient_min = patient.loc[:, [c for c in [
        "patient_id",
        "sex_category",
        "race_category",
        "ethnicity_category",
    ] if c in patient.columns]].copy()
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

    adt_min = adt.loc[:, [c for c in [
        "hospitalization_id",
        "in_dttm",
        "out_dttm",
        "location_category",
        "location_type",
    ] if c in adt.columns]].copy()
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
    icu_bounds["icu_los_hours"] = (
        icu_bounds["last_icu_out"] - icu_bounds["first_icu_in"]
    ).dt.total_seconds() / 3600.0

    all_icu = base.merge(icu_bounds, on="hospitalization_id", how="inner")
    all_icu["admit_year"] = all_icu["admission_dttm"].dt.year
    all_icu["has_geo"] = (
        all_icu.get("county_code", pd.Series(index=all_icu.index)).notna()
        | all_icu.get("census_tract", pd.Series(index=all_icu.index)).notna()
        | all_icu.get("zipcode_five_digit", pd.Series(index=all_icu.index)).notna()
        | all_icu.get("zipcode_nine_digit", pd.Series(index=all_icu.index)).notna()
    )
    return all_icu.sort_values(["admission_dttm", "hospitalization_id"]).reset_index(drop=True)


def build_ohca_poa_cohort(
    all_icu: pd.DataFrame,
    hospital_diagnosis: pd.DataFrame,
) -> pd.DataFrame:
    dx_cols = [
        "hospitalization_id",
        "diagnosis_code",
        "diagnosis_code_format",
        "poa_present",
        "diagnosis_primary",
    ]
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

    return (
        all_icu.merge(ohca_summary, on="hospitalization_id", how="inner")
        .sort_values(["admission_dttm", "hospitalization_id"])
        .reset_index(drop=True)
    )


def build_sepsis_cohort(
    all_icu: pd.DataFrame,
    tables_path: Path,
    file_type: str,
) -> pd.DataFrame:
    try:
        from clifpy.utils.ase import compute_ase
    except ImportError as exc:
        raise ImportError(
            "clifpy is required for the sepsis cohort. Install clifpy to compute ASE."
        ) from exc

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

    onset_col = (
        "ase_onset_w_lactate_dttm"
        if "ase_onset_w_lactate_dttm" in ase.columns
        else "blood_culture_dttm"
    )
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

    return (
        all_icu.merge(ase_first, on="hospitalization_id", how="inner")
        .sort_values(["admission_dttm", "hospitalization_id"])
        .reset_index(drop=True)
    )


def write_outputs(site_name: str, cohorts: dict[str, pd.DataFrame], output_dir: Path) -> None:
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

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output_dir / f"cohort_summary_{site_name}.csv", index=False)


def main() -> None:
    config = load_config()
    site_name = str(config["site_name"])
    tables_path = resolve_tables_path(config)
    output_dir = resolve_output_dir(config)
    file_type = normalize_file_type(config["file_type"])

    patient = read_table(tables_path, file_type, "patient")
    hospitalization = read_table(tables_path, file_type, "hospitalization")
    adt = read_table(tables_path, file_type, "adt")
    hospital_diagnosis = read_table(tables_path, file_type, "hospital_diagnosis")

    all_icu = build_all_icu_cohort(patient, hospitalization, adt)
    sepsis = build_sepsis_cohort(all_icu, tables_path, file_type)
    ohca = build_ohca_poa_cohort(all_icu, hospital_diagnosis)

    write_outputs(
        site_name=site_name,
        output_dir=output_dir,
        cohorts={
            "all_icu_adult": all_icu,
            "sepsis_ase_icu": sepsis,
            "cardiac_arrest_poa_icu": ohca,
        },
    )

    print("Cohort identification complete.")
    print(f"All ICU hospitalizations: {all_icu['hospitalization_id'].nunique()}")
    print(f"Sepsis ICU hospitalizations: {sepsis['hospitalization_id'].nunique()}")
    print(f"Cardiac arrest POA ICU hospitalizations: {ohca['hospitalization_id'].nunique()}")


if __name__ == "__main__":
    main()
