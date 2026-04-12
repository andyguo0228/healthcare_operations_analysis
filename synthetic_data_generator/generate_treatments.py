import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd

from synthetic_data_generator.config import END_DATE
from synthetic_data_generator.utils import weighted_choice


REGIMENS = {
    "Breast Cancer": ["AC-T", "TC", "Herceptin/Perjeta", "Letrozole", "Abemaciclib"],
    "Lung Cancer": ["Carboplatin/Pemetrexed", "Osimertinib", "Pembrolizumab", "Paclitaxel/Carboplatin"],
    "Colorectal Cancer": ["FOLFOX", "FOLFIRI", "CAPOX", "Bevacizumab"],
    "Prostate Cancer": ["Lupron", "Abiraterone", "Docetaxel", "Enzalutamide"],
    "Lymphoma": ["R-CHOP", "ABVD", "Pola-R-CHP", "Observation"],
    "Bladder Cancer": ["Enfortumab vedotin/Pembrolizumab", "Gemcitabine/Cisplatin", "DDMVAC", "Erdafitinib"],
    "Multiple Myeloma": ["VRd", "Daratumumab", "Lenalidomide", "Bortezomib"],
    "Ovarian Cancer": ["Carboplatin/Paclitaxel", "Bevacizumab", "Olaparib"],
    "Pancreatic Cancer": ["FOLFIRINOX", "Gemcitabine/Abraxane", "Observation"],
    "Iron Deficiency Anemia": ["Venofer", "Observation"],
}

TREATMENT_CATEGORIES = {
    "AC-T": "Chemo",
    "TC": "Chemo",
    "Herceptin/Perjeta": "Targeted Therapy",
    "Letrozole": "Hormonal Therapy",
    "Abemaciclib": "Targeted Therapy",
    "Carboplatin/Pemetrexed": "Chemo",
    "Osimertinib": "Targeted Therapy",
    "Pembrolizumab": "Immunotherapy",
    "Paclitaxel/Carboplatin": "Chemo",
    "FOLFOX": "Chemo",
    "FOLFIRI": "Chemo",
    "CAPOX": "Chemo",
    "Bevacizumab": "Targeted Therapy",
    "Lupron": "Hormonal Therapy",
    "Abiraterone": "Hormonal Therapy",
    "Docetaxel": "Chemo",
    "Enzalutamide": "Hormonal Therapy",
    "R-CHOP": "Chemo",
    "ABVD": "Chemo",
    "Pola-R-CHP": "Chemo",
    "VRd": "Chemo",
    "Daratumumab": "Immunotherapy",
    "Lenalidomide": "Targeted Therapy",
    "Bortezomib": "Targeted Therapy",
    "Carboplatin/Paclitaxel": "Chemo",
    "Olaparib": "Targeted Therapy",
    "FOLFIRINOX": "Chemo",
    "Gemcitabine/Abraxane": "Chemo",
    "Venofer": "Supportive Therapy",
    "Observation": "Observation",
    "Enfortumab vedotin/Pembrolizumab": "Immunotherapy",
    "Gemcitabine/Cisplatin": "Chemo",
    "DDMVAC": "Chemo",
    "Erdafitinib": "Targeted Therapy",
}

TREATMENT_ROUTE = {
    "Chemo": "IV",
    "Immunotherapy": "IV",
    "Targeted Therapy": "Oral",
    "Hormonal Therapy": "Injection",
    "Supportive Therapy": "IV",
    "Observation": "None",
}


def choose_regimen(primary_diagnosis: str) -> str:
    choices = REGIMENS[primary_diagnosis]

    if primary_diagnosis == "Iron Deficiency Anemia":
        return weighted_choice(["Venofer", "Observation"], [85, 15])

    if "Observation" in choices:
        weights = [4 if c != "Observation" else 1 for c in choices]
        return weighted_choice(choices, weights)

    return random.choice(choices)


def number_of_treatment_lines(patient_row: pd.Series) -> int:
    diagnosis = patient_row["primary_diagnosis"]
    stage = patient_row["stage"]
    comorbidity = patient_row["comorbidity_score"]

    if diagnosis == "Iron Deficiency Anemia":
        if patient_row["active_treatment_flag"] == 1:
            probs = [0.68, 0.27, 0.05]
            if comorbidity >= 5:
                probs = [0.58, 0.32, 0.10]
            return weighted_choice([1, 2, 3], probs)
        return weighted_choice([0, 1, 2], [0.65, 0.30, 0.05])

    if patient_row["active_treatment_flag"] == 0:
        return weighted_choice([0, 1, 2], [0.55, 0.35, 0.10])

    if stage in {"IV", "High Risk"}:
        probs = [0.38, 0.33, 0.22, 0.07]
        if diagnosis in {"Pancreatic Cancer", "Lung Cancer", "Multiple Myeloma"}:
            probs = [0.30, 0.33, 0.27, 0.10]
        return weighted_choice([1, 2, 3, 4], probs)

    if stage == "III":
        return weighted_choice([1, 2, 3], [0.55, 0.32, 0.13])

    return weighted_choice([1, 2, 3], [0.70, 0.25, 0.05])


def treatment_duration_days(category: str, regimen: str) -> int:
    if regimen == "Venofer":
        duration = int(np.random.triangular(left=7, mode=24, right=90))
        return int(np.clip(duration, 5, 100))
    if category == "Chemo":
        return int(np.clip(np.random.lognormal(mean=4.6, sigma=0.50), 21, 320))
    if category == "Immunotherapy":
        return int(np.clip(np.random.lognormal(mean=5.0, sigma=0.45), 45, 540))
    if category == "Targeted Therapy":
        return int(np.clip(np.random.lognormal(mean=5.2, sigma=0.50), 60, 660))
    if category == "Hormonal Therapy":
        return int(np.clip(np.random.lognormal(mean=5.5, sigma=0.45), 90, 900))
    return int(np.clip(np.random.lognormal(mean=4.2, sigma=0.60), 14, 300))


def treatment_frequency(category: str, route: str, regimen: str) -> str:
    if regimen == "Venofer":
        return weighted_choice(["Q3D", "Q7D"], [70, 30])
    if category == "Chemo":
        return weighted_choice(["Q1W", "Q2W", "Q3W", "Q4W"], [15, 35, 40, 10])
    if category == "Immunotherapy":
        return weighted_choice(["Q2W", "Q3W", "Q4W"], [20, 50, 30])
    if category == "Targeted Therapy" and route == "Oral":
        return "Daily"
    if category == "Hormonal Therapy":
        return weighted_choice(["Monthly", "Q3M"], [60, 40])
    return "Observation"


def treatment_intent(patient_row: pd.Series, regimen: str) -> str:
    if regimen == "Venofer":
        return "Supportive"
    if patient_row["stage"] in {"IV", "High Risk"}:
        return weighted_choice(["Curative", "Maintenance", "Palliative"], [20, 25, 55])
    return weighted_choice(["Curative", "Maintenance", "Palliative"], [50, 30, 20])


def generate_treatments(patients_df: pd.DataFrame, appointments_df: pd.DataFrame) -> pd.DataFrame:
    appointment_grain = appointments_df[["appointment_id", "mrn", "appointment_date"]].drop_duplicates(
        subset=["appointment_id"]
    )
    first_appt = (
        appointment_grain.groupby("mrn", as_index=False)["appointment_date"]
        .min()
        .rename(columns={"appointment_date": "first_appointment_date"})
    )

    merged = patients_df.merge(first_appt, on="mrn", how="left")
    rows = []

    for _, patient in merged.iterrows():
        n_lines = number_of_treatment_lines(patient)
        if n_lines == 0:
            continue

        line_start = patient["first_appointment_date"]

        for line_num in range(1, n_lines + 1):
            regimen = choose_regimen(patient["primary_diagnosis"])
            category = TREATMENT_CATEGORIES[regimen]
            route = TREATMENT_ROUTE[category]

            if line_num == 1:
                if np.random.random() < 0.25:
                    start_offset = random.randint(0, 4)
                else:
                    start_offset = int(np.clip(np.random.normal(10, 9), 0, 40))
            else:
                if np.random.random() < 0.20:
                    start_offset = int(np.clip(np.random.normal(70, 28), 21, 180))
                else:
                    start_offset = int(np.clip(np.random.normal(33, 17), 7, 120))

            line_start = line_start + timedelta(days=start_offset)
            duration_days = treatment_duration_days(category, regimen)

            if line_num > 1 and np.random.random() < 0.18:
                duration_days = int(np.clip(duration_days * np.random.uniform(0.45, 0.85), 14, 540))

            line_end = line_start + timedelta(days=duration_days)

            if line_start > END_DATE:
                break

            active_flag = 1 if line_start <= END_DATE <= line_end else 0
            if line_end > END_DATE:
                line_end = END_DATE

            rows.append(
                {
                    "treatment_id": f"TRT-{uuid.uuid4().hex[:10].upper()}",
                    "patient_id": patient["patient_id"],
                    "line_of_therapy": line_num,
                    "regimen_name": regimen,
                    "treatment_category": category,
                    "route": route,
                    "frequency": treatment_frequency(category, route, regimen),
                    "intent": treatment_intent(patient, regimen),
                    "start_date": line_start,
                    "end_date": line_end,
                    "active_flag": active_flag,
                }
            )

            line_start = line_end

    return pd.DataFrame(rows).sort_values(["patient_id", "line_of_therapy"]).reset_index(drop=True)


if __name__ == "__main__":
    from synthetic_data_generator.generate_appointments import generate_appointments
    from synthetic_data_generator.generate_patients import generate_patients
    from synthetic_data_generator.generate_providers import generate_providers

    patients = generate_patients()
    providers = generate_providers()
    appointments = generate_appointments(patients, providers)
    df = generate_treatments(patients, appointments)
    print(df.head())
    print(df[df["regimen_name"] == "Venofer"].head())