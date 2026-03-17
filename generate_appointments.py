import random
import uuid
from datetime import timedelta

import numpy as np
import pandas as pd

from config import (
    APPOINTMENT_STATUS,
    END_DATE,
    START_DATE,
    STATUS_WEIGHTS,
    VISIT_TYPES,
)
from utils import compute_duration_minutes, random_date, random_datetime_in_business_hours, weighted_choice


EXAM_ROOMS = [f"Exam Rm {i}" for i in range(1, 25)]
INFUSION_ROOMS = [f"Infusion Bay {i}" for i in range(1, 17)]


ROOM_TYPE_MAP = {
    "Registration": "Front Desk",
    "Lab Waiting Room": "Lab",
    "Lab": "Lab",
    "Phlebotomy": "Lab",
    "Waiting Room": "Waiting Room",
    "Px Living Room": "Waiting Room",
    "MA Intake": "Exam Room",
    "MD Office": "Exam Room",
    "Tx Living Room": "Other",
    "Waiting for RN": "Other",
    "Ready to Check Out": "Other",
    "Cancelled": "Status",
    "No Show": "Status",
}


def patient_visit_count(patient_row: pd.Series) -> int:
    if patient_row["primary_diagnosis"] == "Iron Deficiency Anemia":
        base = 2
        if patient_row["active_treatment_flag"] == 1:
            base += 3
        extra = np.random.poisson(1)
        return int(np.clip(base + extra, 1, 8))

    base = 2
    if patient_row["active_treatment_flag"] == 1:
        base += 5
    if patient_row["primary_diagnosis"] in {"Leukemia", "Lymphoma", "Multiple Myeloma"}:
        base += 2
    if patient_row["stage"] in {"III", "IV", "High Risk"}:
        base += 2

    extra = np.random.poisson(2)
    return int(np.clip(base + extra, 1, 18))


def choose_visit_type(patient_row: pd.Series, visit_index: int) -> str:
    diagnosis = patient_row["primary_diagnosis"]

    if visit_index == 0:
        return weighted_choice(["New Patient", "Follow-up"], [80, 20])

    if diagnosis == "Iron Deficiency Anemia":
        if patient_row["active_treatment_flag"] == 1:
            return weighted_choice(
                ["Follow-up", "Infusion", "Lab Review", "Urgent Visit"],
                [30, 50, 15, 5],
            )
        return weighted_choice(
            ["Follow-up", "Lab Review", "Infusion"],
            [65, 25, 10],
        )

    if patient_row["active_treatment_flag"] == 1:
        return weighted_choice(VISIT_TYPES, [3, 38, 35, 14, 10])

    return weighted_choice(VISIT_TYPES, [2, 55, 8, 25, 10])


def choose_status(visit_type: str) -> str:
    if visit_type == "Infusion":
        return weighted_choice(APPOINTMENT_STATUS, [90, 4, 6])
    return weighted_choice(APPOINTMENT_STATUS, STATUS_WEIGHTS)


def provider_for_patient_visit(providers_df: pd.DataFrame) -> str:
    return providers_df.sample(1, random_state=random.randint(1, 999999)).iloc[0]["provider_id"]


def build_patient_flow(visit_type: str, status: str) -> list[str]:
    if status == "Cancelled":
        return ["Cancelled"]

    if status == "No Show":
        return ["No Show"]

    if visit_type == "Follow-up":
        if weighted_choice([0, 1], [85, 15]) == 1:
            return [
                "Lab Waiting Room",
                "Lab",
                "Phlebotomy",
                "Px Living Room",
                "Exam Room",
                "MD Office",
                "Tx Living Room",
                "Waiting for RN",
                "Infusion Room",
                "Ready to Check Out",
            ]
        return ["Lab Waiting Room", "Lab", "Phlebotomy", "Px Living Room", "Exam Room", "Ready to Check Out"]

    if visit_type == "New Patient":
        if weighted_choice([0, 1], [90, 10]) == 1:
            return [
                "Registration",
                "Lab Waiting Room",
                "Lab",
                "Phlebotomy",
                "Px Living Room",
                "MA Intake",
                "Exam Room",
                "MD Office",
                "Tx Living Room",
                "Waiting for RN",
                "Infusion Room",
                "Ready to Check Out",
            ]
        return [
            "Registration",
            "Lab Waiting Room",
            "Lab",
            "Phlebotomy",
            "Px Living Room",
            "MA Intake",
            "Exam Room",
            "MD Office",
            "Ready to Check Out",
        ]

    if visit_type == "Infusion":
        return [
            "Lab Waiting Room",
            "Lab",
            "Phlebotomy",
            "Px Living Room",
            "Exam Room",
            "MD Office",
            "Tx Living Room",
            "Waiting for RN",
            "Infusion Room",
            "Ready to Check Out",
        ]

    if visit_type == "Lab Review":
        return ["Lab Waiting Room", "Lab", "Phlebotomy", "Px Living Room", "Exam Room", "Ready to Check Out"]

    return ["Waiting Room", "MA Intake", "Exam Room", "Ready to Check Out"]


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
        return "Other"
    return ROOM_TYPE_MAP.get(room_name, "Other")


def room_duration_bounds(room_state: str, visit_type: str) -> tuple[int, int]:
    bounds = {
        "Registration": (3, 9),
        "Lab Waiting Room": (4, 18),
        "Lab": (3, 12),
        "Phlebotomy": (4, 16),
        "Waiting Room": (4, 16),
        "Px Living Room": (5, 20),
        "MA Intake": (4, 12),
        "Exam Room": (8, 30),
        "MD Office": (8, 28),
        "Tx Living Room": (4, 20),
        "Waiting for RN": (3, 16),
        "Infusion Room": (45, 240),
        "Ready to Check Out": (4, 20),
    }
    if room_state == "Infusion Room" and visit_type != "Infusion":
        return (25, 120)
    return bounds.get(room_state, (3, 12))


def allocate_room_durations(patient_flow: list[str], total_minutes: int, visit_type: str) -> list[int]:
    total_minutes = max(total_minutes, len(patient_flow))

    base = []
    for room_state in patient_flow:
        low, high = room_duration_bounds(room_state, visit_type)
        base.append(random.randint(low, high))

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

    arrival_offset_min = int(np.clip(np.random.normal(3, 9), -20, 35))
    check_in_dt = scheduled_dt + timedelta(minutes=arrival_offset_min)

    if visit_type == "Infusion":
        wait_to_room = random.randint(5, 25)
        wait_to_provider = random.randint(8, 30)
        provider_time = random.randint(8, 20)
        infusion_time = random.randint(45, 240)
        post_time = random.randint(5, 20)

        roomed_dt = check_in_dt + timedelta(minutes=wait_to_room)
        provider_seen_dt = roomed_dt + timedelta(minutes=wait_to_provider)
        checkout_dt = provider_seen_dt + timedelta(minutes=provider_time + infusion_time + post_time)

    elif visit_type == "New Patient":
        wait_to_room = random.randint(8, 30)
        wait_to_provider = random.randint(5, 20)
        provider_time = random.randint(30, 65)
        post_time = random.randint(5, 15)

        roomed_dt = check_in_dt + timedelta(minutes=wait_to_room)
        provider_seen_dt = roomed_dt + timedelta(minutes=wait_to_provider)
        checkout_dt = provider_seen_dt + timedelta(minutes=provider_time + post_time)

    elif visit_type == "Urgent Visit":
        wait_to_room = random.randint(3, 18)
        wait_to_provider = random.randint(2, 12)
        provider_time = random.randint(15, 35)
        post_time = random.randint(3, 10)

        roomed_dt = check_in_dt + timedelta(minutes=wait_to_room)
        provider_seen_dt = roomed_dt + timedelta(minutes=wait_to_provider)
        checkout_dt = provider_seen_dt + timedelta(minutes=provider_time + post_time)

    elif visit_type == "Lab Review":
        wait_to_room = random.randint(4, 18)
        wait_to_provider = random.randint(2, 10)
        provider_time = random.randint(8, 18)
        post_time = random.randint(2, 8)

        roomed_dt = check_in_dt + timedelta(minutes=wait_to_room)
        provider_seen_dt = roomed_dt + timedelta(minutes=wait_to_provider)
        checkout_dt = provider_seen_dt + timedelta(minutes=provider_time + post_time)

    else:
        wait_to_room = random.randint(5, 22)
        wait_to_provider = random.randint(3, 15)
        provider_time = random.randint(10, 25)
        post_time = random.randint(3, 10)

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

    for _, patient in patients_df.iterrows():
        n_visits = patient_visit_count(patient)
        first_visit_date = random_date(START_DATE, END_DATE - timedelta(days=30))
        visit_dates = [first_visit_date]

        for _ in range(n_visits - 1):
            gap = int(np.clip(np.random.normal(28, 18), 7, 90))
            next_date = visit_dates[-1] + timedelta(days=gap)
            if next_date > END_DATE:
                break
            visit_dates.append(next_date)

        for idx, visit_date in enumerate(sorted(visit_dates)):
            visit_type = choose_visit_type(patient, idx)
            status = choose_status(visit_type)

            provider_id = provider_for_patient_visit(providers_df)
            scheduled_dt = random_datetime_in_business_hours(visit_date)
            flow = generate_flow_times(scheduled_dt, visit_type, status)
            patient_flow = build_patient_flow(visit_type, status)

            appointment_id = f"APPT-{uuid.uuid4().hex[:10].upper()}"
            patient_flow_str = " -> ".join(patient_flow)

            common_values = {
                "appointment_id": appointment_id,
                "patient_id": patient["patient_id"],
                "mrn": patient["mrn"],
                "provider_id": provider_id,
                "appointment_date": scheduled_dt.date(),
                "visit_type": visit_type,
                "status": status,
                "scheduled_datetime": flow["scheduled_datetime"],
                "check_in_datetime": flow["check_in_datetime"],
                "roomed_datetime": flow["roomed_datetime"],
                "provider_seen_datetime": flow["provider_seen_datetime"],
                "checkout_datetime": flow["checkout_datetime"],
                "arrival_delay_min": compute_duration_minutes(flow["scheduled_datetime"], flow["check_in_datetime"]),
                "wait_to_room_min": compute_duration_minutes(flow["check_in_datetime"], flow["roomed_datetime"]),
                "wait_to_provider_min": compute_duration_minutes(flow["roomed_datetime"], flow["provider_seen_datetime"]),
                "provider_cycle_min": compute_duration_minutes(flow["provider_seen_datetime"], flow["checkout_datetime"]),
                "visit_duration_min": compute_duration_minutes(flow["check_in_datetime"], flow["checkout_datetime"]),
                "total_los_min": compute_duration_minutes(flow["scheduled_datetime"], flow["checkout_datetime"]),
                "patient_flow": patient_flow_str,
                "new_patient_flag": 1 if visit_type == "New Patient" else 0,
                "infusion_flag": 1 if visit_type == "Infusion" else 0,
                "urgent_flag": 1 if visit_type == "Urgent Visit" else 0,
            }

            if status in {"Cancelled", "No Show"}:
                status_room = patient_flow[0]
                rows.append(
                    {
                        **common_values,
                        "room": status_room,
                        "room_type": room_type_for(status_room),
                        "room_datetime": flow["scheduled_datetime"],
                        "duration_min": None,
                        "room_sequence": 1,
                    }
                )
                continue

            total_visit_minutes = compute_duration_minutes(flow["check_in_datetime"], flow["checkout_datetime"]) or 0
            durations = allocate_room_durations(patient_flow, total_visit_minutes, visit_type)

            room_start = flow["check_in_datetime"]
            for sequence, (room_state, duration_min) in enumerate(zip(patient_flow, durations), start=1):
                room_name = resolve_room_name(room_state)
                rows.append(
                    {
                        **common_values,
                        "room": room_name,
                        "room_type": room_type_for(room_name),
                        "room_datetime": room_start,
                        "duration_min": duration_min,
                        "room_sequence": sequence,
                    }
                )
                room_start = room_start + timedelta(minutes=duration_min)

    return pd.DataFrame(rows).sort_values(["room_datetime", "patient_id", "appointment_id", "room_sequence"]).reset_index(drop=True)


if __name__ == "__main__":
    from generate_patients import generate_patients
    from generate_providers import generate_providers

    patients = generate_patients()
    providers = generate_providers()
    df = generate_appointments(patients, providers)
    print(df.head())
