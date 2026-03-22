from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import (
    DIAGNOSIS_GROUPS,
    INSURANCE_TYPES,
    MALIGNANT_CANCERS,
    MALIGNANT_WEIGHTS,
    NUM_PATIENTS,
    RACES,
    RACE_WEIGHTS,
)
from utils import (
    age_from_dob,
    fake,
    generate_dob,
    generate_mrn,
    generate_zip_code,
    weighted_choice,
)


@dataclass
class PatientProfile:
    patient_id: str
    mrn: str
    first_name: str
    last_name: str
    sex: str
    dob: object
    age: int
    race: str
    zip_code: str
    insurance_type: str
    diagnosis_group: str
    primary_diagnosis: str
    stage: str
    comorbidity_score: int
    smoking_status: str
    active_treatment_flag: int
    deceased_flag: int


def assign_malignant_sex(diagnosis: str) -> str:
    if diagnosis == "Prostate Cancer":
        return "Male"
    if diagnosis == "Ovarian Cancer":
        return "Female"
    if diagnosis == "Breast Cancer":
        return weighted_choice(["Female", "Male"], [98, 2])
    return weighted_choice(["Female", "Male"], [52, 48])


def assign_stage(diagnosis: str) -> str:
    if diagnosis in {"Lymphoma", "Multiple Myeloma"}:
        return weighted_choice(["Low Risk", "Intermediate Risk", "High Risk"], [35, 40, 25])
    if diagnosis == "Iron Deficiency Anemia":
        return "N/A"
    return weighted_choice(["I", "II", "III", "IV"], [20, 28, 27, 25])


def smoking_status_for_dx(diagnosis: str) -> str:
    if diagnosis == "Lung Cancer":
        return weighted_choice(["Never", "Former", "Current"], [20, 50, 30])
    return weighted_choice(["Never", "Former", "Current"], [55, 30, 15])


def insurance_for_age(age: int) -> str:
    if age < 65:
        return weighted_choice(INSURANCE_TYPES, [60, 8, 25, 7])
    return weighted_choice(INSURANCE_TYPES, [20, 60, 15, 5])


def choose_diagnosis_group() -> str:
    keys = list(DIAGNOSIS_GROUPS.keys())
    weights = list(DIAGNOSIS_GROUPS.values())
    return weighted_choice(keys, weights)


def choose_primary_diagnosis(group: str) -> str:
    if group == "ida":
        return "Iron Deficiency Anemia"
    return weighted_choice(MALIGNANT_CANCERS, MALIGNANT_WEIGHTS)


def assign_sex_for_diagnosis(group: str, diagnosis: str) -> str:
    if group == "ida":
        return weighted_choice(["Female", "Male"], [70, 30])
    return assign_malignant_sex(diagnosis)


def active_treatment_flag_for_dx(group: str, diagnosis: str) -> int:
    if group == "ida":
        return weighted_choice([1, 0], [65, 35])
    return weighted_choice([1, 0], [72, 28])


def deceased_flag_for_dx(group: str) -> int:
    if group == "ida":
        return weighted_choice([0, 1], [995, 5])
    return weighted_choice([0, 1], [97, 3])


def generate_patients(n: int = NUM_PATIENTS) -> pd.DataFrame:
    rows = []

    for i in range(1, n + 1):
        group = choose_diagnosis_group()
        diagnosis = choose_primary_diagnosis(group)
        sex = assign_sex_for_diagnosis(group, diagnosis)

        dob = generate_dob()
        age = age_from_dob(dob)

        first_name = fake.first_name_female() if sex == "Female" else fake.first_name_male()
        last_name = fake.last_name()

        if group == "ida":
            comorbidity_score = int(np.clip(np.random.poisson(lam=max(1.0, age / 40)), 0, 6))
        else:
            comorbidity_score = int(np.clip(np.random.poisson(lam=max(1.2, age / 30)), 0, 8))

        patient = PatientProfile(
            patient_id=f"PT{100000 + i}",
            mrn=generate_mrn(i),
            first_name=first_name,
            last_name=last_name,
            sex=sex,
            dob=dob,
            age=age,
            race=weighted_choice(RACES, RACE_WEIGHTS),
            zip_code=generate_zip_code(),
            insurance_type=insurance_for_age(age),
            diagnosis_group=group,
            primary_diagnosis=diagnosis,
            stage=assign_stage(diagnosis),
            comorbidity_score=comorbidity_score,
            smoking_status=smoking_status_for_dx(diagnosis),
            active_treatment_flag=active_treatment_flag_for_dx(group, diagnosis),
            deceased_flag=deceased_flag_for_dx(group),
        )

        rows.append(patient.__dict__)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate_patients()
    print(df.head())
    print(df["primary_diagnosis"].value_counts().head(10))
