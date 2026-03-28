import numpy as np
import pandas as pd

from synthetic_data_generator.config import NUM_PROVIDERS
from synthetic_data_generator.utils import fake, weighted_choice


def generate_providers(n: int = NUM_PROVIDERS) -> pd.DataFrame:
    rows = []

    for i in range(1, n + 1):
        sex = weighted_choice(["Female", "Male"], [50, 50])
        first_name = fake.first_name_female() if sex == "Female" else fake.first_name_male()
        last_name = fake.last_name()

        rows.append(
            {
                "provider_id": f"PR{1000 + i}",
                "provider_name": f"Dr. {first_name} {last_name}",
                "years_experience": int(np.clip(np.random.normal(12, 6), 1, 35)),
                "fte": weighted_choice([1.0, 0.8, 0.6], [70, 20, 10]),
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate_providers()
    print(df.head())
