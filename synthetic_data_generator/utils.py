import random
from datetime import date, datetime, timedelta

import numpy as np
from faker import Faker

from synthetic_data_generator.config import SEED

random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)


def weighted_choice(options, weights):
    return random.choices(options, weights=weights, k=1)[0]


def random_date(start: date, end: date) -> date:
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


def random_datetime_in_business_hours(d: date) -> datetime:
    hour = weighted_choice(
        [8, 9, 10, 11, 12, 13, 14, 15, 16],
        [8, 12, 14, 12, 6, 10, 12, 10, 6],
    )
    minute = random.randint(0, 59)
    return datetime(d.year, d.month, d.day, hour, minute)


def random_business_date(start: date, end: date) -> date:
    """Return a random weekday (Mon–Fri) between start and end."""
    d = random_date(start, end)
    # Nudge Saturday → Friday, Sunday → Friday
    if d.weekday() == 5:
        d -= timedelta(days=1)
    elif d.weekday() == 6:
        d -= timedelta(days=2)
    return max(start, d)


def next_weekday(d: date) -> date:
    """Push a weekend date to a nearby weekday (Friday or Monday, 50/50)."""
    if d.weekday() == 5:  # Saturday — shift to Friday or Monday
        return d + timedelta(days=random.choice([-1, 2]))
    if d.weekday() == 6:  # Sunday — shift to Friday or Monday
        return d + timedelta(days=random.choice([-2, 1]))
    return d


def age_from_dob(dob: date, ref: date | None = None) -> int:
    ref = ref or date.today()
    return ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))


def generate_dob(min_age=18, max_age=90) -> date:
    today = date.today()
    age = random.randint(min_age, max_age)
    year = today.year - age
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return date(year, month, day)


def generate_mrn(i: int) -> str:
    return f"MRN{100000 + i}"


def generate_zip_code() -> str:
    return random.choice(
        ["11373", "11375", "11354", "11101", "10016", "10019", "11201", "11215", "10461", "11004"]
    )


def compute_duration_minutes(start_dt, end_dt):
    if start_dt is None or end_dt is None:
        return None
    return int((end_dt - start_dt).total_seconds() // 60)