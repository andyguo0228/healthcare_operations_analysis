import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd

from synthetic_data_generator.config import (
    APPOINTMENT_STATUS,
    END_DATE,
    START_DATE,
    STATUS_WEIGHTS,
    VISIT_TYPES,
)
from synthetic_data_generator.utils import compute_duration_minutes, random_business_date, random_date, random_datetime_in_business_hours, next_weekday, weighted_choice


EXAM_ROOMS = [f"Exam Rm {i}" for i in range(1, 25)]
INFUSION_ROOMS = [f"Infusion Bay {i}" for i in range(1, 25)]


ROOM_TYPE_MAP = {
    "Registration": "Front Desk",
    "Lab Waiting Room": "Lab",
    "Lab": "Lab",
    "Waiting Room": "Exam Room",
    "Infusion Waiting Room": "Infusion Room",
    "Ready to Check Out": "Front Desk",
    "Checked Out": "Status",
    "Cancelled": "Status",
    "No Show": "Status",
}


def patient_visit_count(patient_row: pd.Series) -> int:
    # Wider sigma creates a longer tail — some patients have many more/fewer visits than average
    volatility = float(np.clip(np.random.lognormal(mean=-0.1, sigma=0.65), 0.40, 3.2))

    if patient_row["primary_diagnosis"] == "Iron Deficiency Anemia":
        base = 2
        if patient_row["active_treatment_flag"] == 1:
            base += 3
        if patient_row["comorbidity_score"] >= 4:
            base += 1
        extra = np.random.poisson(1)
        return int(np.clip(round((base + extra) * volatility), 1, 16))

    base = 2
    if patient_row["active_treatment_flag"] == 1:
        base += 5
    if patient_row["primary_diagnosis"] in {"Lymphoma", "Multiple Myeloma"}:
        base += 2
    if patient_row["stage"] in {"III", "IV", "High Risk"}:
        base += 2
    if patient_row["comorbidity_score"] >= 6:
        base += 1

    extra = np.random.poisson(2)
    return int(np.clip(round((base + extra) * volatility), 1, 36))


def choose_visit_type(patient_row: pd.Series, visit_index: int) -> str:
    diagnosis = patient_row["primary_diagnosis"]

    if visit_index == 0:
        return weighted_choice(["New Patient", "Follow-up"], [80, 20])

    if diagnosis == "Iron Deficiency Anemia":
        if patient_row["active_treatment_flag"] == 1:
            return weighted_choice(
                ["Follow-up", "Infusion", "Walk In Visits"],
                [35, 59, 6],
            )
        return weighted_choice(
            ["Follow-up", "Infusion"],
            [87, 13],
        )

    if patient_row["active_treatment_flag"] == 1:
        weights = [3, 38, 35, 10]
        if patient_row["stage"] in {"IV", "High Risk"}:
            weights = [2, 30, 40, 16]
        elif patient_row["comorbidity_score"] >= 6:
            weights = [2, 33, 28, 19]
        return weighted_choice(VISIT_TYPES, weights)

    weights = [2, 55, 8, 10]
    if patient_row["comorbidity_score"] >= 5:
        weights = [2, 50, 8, 17]
    return weighted_choice(VISIT_TYPES, weights)


def choose_status(visit_type: str, patient_row: pd.Series, scheduled_dt=None) -> str:
    weather_months = {1, 2, 7, 8, 12}
    month = scheduled_dt.month if scheduled_dt is not None else None

    if visit_type == "Infusion":
        weights = [90, 4, 6]
    elif visit_type == "Walk In Visits":
        weights = [93, 3, 4]
    elif visit_type == "New Patient":
        weights = [80, 8, 12]
    else:
        weights = list(STATUS_WEIGHTS)

    if month in weather_months:
        weights[1] += 2
        weights[2] += 1
        weights[0] = max(60, 100 - weights[1] - weights[2])

    if patient_row["comorbidity_score"] >= 6:
        weights[2] += 2
        weights[1] += 1
        weights[0] = max(55, 100 - weights[1] - weights[2])

    return weighted_choice(APPOINTMENT_STATUS, weights)


def provider_for_patient_visit(providers_df: pd.DataFrame, preferred_id: str | None = None) -> str:
    # 70% chance of continuity — patients tend to see the same provider
    if preferred_id is not None and random.random() < 0.70:
        return preferred_id
    return providers_df.sample(1, random_state=random.randint(1, 999999)).iloc[0]["provider_id"]


def build_patient_flow(visit_type: str, status: str) -> list[str]:
    if status == "Cancelled":
        return ["Cancelled"]

    if status == "No Show":
        return ["No Show"]

    if visit_type == "Follow-up":
        return ["Lab Waiting Room", "Lab", "Waiting Room", "Exam Room", "Ready to Check Out", "Checked Out"]

    if visit_type == "New Patient":
        return [
            "Registration",
            "Waiting Room",
            "Exam Room",
            "Lab Waiting Room",
            "Lab",
            "Ready to Check Out",
            "Checked Out",
        ]

    if visit_type == "Infusion":
        return [
            "Lab Waiting Room",
            "Lab",
            "Waiting Room",
            "Exam Room",
            "Infusion Waiting Room",
            "Infusion Room",
            "Ready to Check Out",
            "Checked Out",
        ]

    return ["Lab Waiting Room", "Lab", "Waiting Room", "Exam Room", "Ready to Check Out", "Checked Out"]


def resolve_room_name(room_state: str) -> str:
    if room_state == "Exam Room":
        return random.choice(EXAM_ROOMS)
    if room_state == "Infusion Room":
        return random.choice(INFUSION_ROOMS)
    return room_state


def room_type_for(room_name: str) -> str:
    if room_name.startswith("Exam Rm"):
        return "Exam Room"
    if room_name.startswith("Infusion Bay"):
        return "Infusion Room"
    return ROOM_TYPE_MAP.get(room_name, "Other")


def room_duration_bounds(room_state: str, visit_type: str) -> tuple[int, int]:
    bounds = {
        "Registration": (3, 9),
        "Lab Waiting Room": (4, 18),
        "Lab": (3, 12),
        "Waiting Room": (4, 16),
        "Exam Room": (8, 30),
        "Infusion Waiting Room": (4, 20),
        "Infusion Room": (45, 240),
        "Ready to Check Out": (4, 20),
        "Checked Out": (1, 5),
    }
    if room_state == "Infusion Room" and visit_type != "Infusion":
        return (25, 120)
    return bounds.get(room_state, (3, 12))


def allocate_room_durations(patient_flow: list[str], total_minutes: int, visit_type: str) -> list[int]:
    total_minutes = max(total_minutes, len(patient_flow))

    base = []
    # Wider sigma + higher ceiling creates sporadic days where waits are dramatically longer or shorter
    shock_multiplier = float(np.clip(np.random.lognormal(mean=0.0, sigma=0.55), 0.45, 3.5))
    for room_state in patient_flow:
        low, high = room_duration_bounds(room_state, visit_type)
        sampled = random.randint(low, high)
        if room_state in {"Waiting Room", "Lab Waiting Room", "Infusion Waiting Room"}:
            sampled = int(round(sampled * shock_multiplier))
        base.append(max(1, sampled))

    base_sum = sum(base)
    scaled = [max(1, int(round(value * total_minutes / base_sum))) for value in base]

    diff = total_minutes - sum(scaled)
    idx = 0
    max_iter = 10000
    while diff != 0 and idx < max_iter:
        i = idx % len(scaled)
        if diff > 0:
            scaled[i] += 1
            diff -= 1
        elif scaled[i] > 1:
            scaled[i] -= 1
            diff += 1
        idx += 1

    return scaled


def generate_flow_times(scheduled_dt, visit_type: str, status: str) -> dict:
    if status in {"Cancelled", "No Show"}:
        return {
            "scheduled_datetime": scheduled_dt,
            "check_in_datetime": None,
            "roomed_datetime": None,
            "provider_seen_datetime": None,
            "checkout_datetime": None,
        }

    # Wider sigma and heavier tails — patients arrive very early or very late more often
    arrival_offset_min = int(np.clip(np.random.normal(4, 16), -50, 90))
    if np.random.random() < 0.22:
        arrival_offset_min += random.choice([-45, -30, -20, 25, 40, 60, 80])
    check_in_dt = scheduled_dt + timedelta(minutes=arrival_offset_min)

    # Helper: lognormal wait — produces realistic right-skewed distributions
    def _lognorm_wait(median: float, sigma: float, lo: int, hi: int) -> int:
        return int(np.clip(np.random.lognormal(mean=np.log(median), sigma=sigma), lo, hi))

    if visit_type == "Infusion":
        wait_to_room = _lognorm_wait(12, 0.65, 2, 80)
        wait_to_provider = _lognorm_wait(15, 0.60, 3, 75)
        provider_time = _lognorm_wait(13, 0.50, 5, 50)
        infusion_time = _lognorm_wait(105, 0.55, 30, 420)
        post_time = _lognorm_wait(10, 0.55, 3, 45)

        roomed_dt = check_in_dt + timedelta(minutes=wait_to_room)
        provider_seen_dt = roomed_dt + timedelta(minutes=wait_to_provider)
        checkout_dt = provider_seen_dt + timedelta(minutes=provider_time + infusion_time + post_time)

    elif visit_type == "New Patient":
        wait_to_room = _lognorm_wait(16, 0.65, 3, 90)
        wait_to_provider = _lognorm_wait(11, 0.60, 3, 60)
        provider_time = _lognorm_wait(45, 0.45, 20, 120)
        post_time = _lognorm_wait(9, 0.55, 3, 35)

        roomed_dt = check_in_dt + timedelta(minutes=wait_to_room)
        provider_seen_dt = roomed_dt + timedelta(minutes=wait_to_provider)
        checkout_dt = provider_seen_dt + timedelta(minutes=provider_time + post_time)

    elif visit_type == "Walk In Visits":
        wait_to_room = _lognorm_wait(8, 0.70, 1, 50)
        wait_to_provider = _lognorm_wait(6, 0.65, 1, 35)
        provider_time = _lognorm_wait(22, 0.50, 8, 70)
        post_time = _lognorm_wait(6, 0.55, 2, 25)

        roomed_dt = check_in_dt + timedelta(minutes=wait_to_room)
        provider_seen_dt = roomed_dt + timedelta(minutes=wait_to_provider)
        checkout_dt = provider_seen_dt + timedelta(minutes=provider_time + post_time)

    else:
        wait_to_room = _lognorm_wait(11, 0.65, 2, 65)
        wait_to_provider = _lognorm_wait(8, 0.60, 2, 45)
        provider_time = _lognorm_wait(16, 0.50, 6, 55)
        post_time = _lognorm_wait(6, 0.55, 2, 25)

        roomed_dt = check_in_dt + timedelta(minutes=wait_to_room)
        provider_seen_dt = roomed_dt + timedelta(minutes=wait_to_provider)
        checkout_dt = provider_seen_dt + timedelta(minutes=provider_time + post_time)

    return {
        "scheduled_datetime": scheduled_dt,
        "check_in_datetime": check_in_dt,
        "roomed_datetime": roomed_dt,
        "provider_seen_datetime": provider_seen_dt,
        "checkout_datetime": checkout_dt,
    }


def generate_appointments(patients_df: pd.DataFrame, providers_df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    # Assign each patient a primary provider for continuity of care
    primary_provider_map = {
        mrn: providers_df.sample(1, random_state=random.randint(1, 999999)).iloc[0]["provider_id"]
        for mrn in patients_df["mrn"]
    }

    for _, patient in patients_df.iterrows():
        n_visits = patient_visit_count(patient)
        # Use business dates only — clinics don't schedule on weekends
        first_visit_date = random_business_date(START_DATE, END_DATE - timedelta(days=30))
        visit_dates = [first_visit_date]

        for _ in range(n_visits - 1):
            if patient["active_treatment_flag"] == 1 and np.random.random() < 0.35:
                gap = int(np.clip(np.random.normal(11, 8), 3, 35))
            elif np.random.random() < 0.20:
                gap = int(np.clip(np.random.normal(74, 35), 28, 210))
            else:
                gap = int(np.clip(np.random.normal(32, 25), 5, 150))

            # Occasional moderate delay
            if np.random.random() < 0.06:
                gap += random.randint(30, 120)
            # Rare "lost to follow-up then returned" gap (~3% of inter-visit intervals)
            if np.random.random() < 0.03:
                gap += random.randint(180, 540)

            next_date = next_weekday(visit_dates[-1] + timedelta(days=gap))
            if next_date > END_DATE:
                break
            visit_dates.append(next_date)

        primary_provider = primary_provider_map[patient["mrn"]]

        for idx, visit_date in enumerate(sorted(visit_dates)):
            visit_type = choose_visit_type(patient, idx)
            provider_id = provider_for_patient_visit(providers_df, preferred_id=primary_provider)
            scheduled_dt = random_datetime_in_business_hours(visit_date)
            status = choose_status(visit_type, patient, scheduled_dt)
            flow = generate_flow_times(scheduled_dt, visit_type, status)
            patient_flow = build_patient_flow(visit_type, status)

            appointment_id = f"APPT-{uuid.uuid4().hex[:10].upper()}"

            common_values = {
                "appointment_id": appointment_id,
                "mrn": patient["mrn"],
                "provider_id": provider_id,
                "appointment_date": scheduled_dt.date(),
                "visit_type": visit_type,
                "status": status,
                "new_patient_flag": 1 if visit_type == "New Patient" else 0,
                "infusion_flag": 1 if visit_type == "Infusion" else 0,
                "urgent_flag": 1 if visit_type == "Walk In Visits" else 0,
            }

            if status in {"Cancelled", "No Show"}:
                status_room = patient_flow[0]
                rows.append(
                    {
                        **common_values,
                        "room": status_room,
                        "room_type": room_type_for(status_room),
                        "room_timestamp": flow["scheduled_datetime"],
                    }
                )
                continue

            total_visit_minutes = compute_duration_minutes(flow["check_in_datetime"], flow["checkout_datetime"]) or 0
            durations = allocate_room_durations(patient_flow, total_visit_minutes, visit_type)

            room_start = flow["check_in_datetime"]
            for room_state, duration_min in zip(patient_flow, durations):
                room_name = resolve_room_name(room_state)
                rows.append(
                    {
                        **common_values,
                        "room": room_name,
                        "room_type": room_type_for(room_name),
                        "room_timestamp": room_start,
                    }
                )
                room_start = room_start + timedelta(minutes=duration_min)

    df = pd.DataFrame(rows).sort_values(["room_timestamp", "appointment_id"]).reset_index(drop=True)
    # Duration is derived from room status transitions within each appointment flow.
    df["duration"] = (
        df.groupby("appointment_id")["room_timestamp"]
        .diff()
        .dt.total_seconds()
        .div(60)
        .groupby(df["appointment_id"])
        .shift(-1)
    )
    return df


if __name__ == "__main__":
    from synthetic_data_generator.generate_patients import generate_patients
    from synthetic_data_generator.generate_providers import generate_providers

    patients = generate_patients()
    providers = generate_providers()
    df = generate_appointments(patients, providers)
    print(df.head())
