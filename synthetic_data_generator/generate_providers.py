import numpy as np
import pandas as pd


PROVIDER_NAMES = [
    "Nina House, MD",
    "Aaron Quinn, MD",
    "John Murphy, MD",
    "Marcus Bailey, MD",
    "Sophia Grey, MD",
    "Adrian Shepherd, MD",
    "Spencer Reed, MD",
    "Owen Strange, MD",
]


def generate_providers(n: int = len(PROVIDER_NAMES)) -> pd.DataFrame:
    if n > len(PROVIDER_NAMES):
        raise ValueError(f"Requested {n} providers but only {len(PROVIDER_NAMES)} names are configured.")

    rows = []

    for i in range(1, n + 1):
        rows.append(
            {
                "provider_id": f"PR{1000 + i}",
                "provider_name": PROVIDER_NAMES[i - 1],
                "years_experience": int(np.clip(np.random.normal(12, 6), 1, 35)),
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate_providers()
    print(df.head())
