import pandas as pd

from config import END_DATE, OUTPUT_DIR, START_DATE
from generate_appointments import generate_appointments
from generate_patients import generate_patients
from generate_providers import generate_providers
from generate_treatments import generate_treatments


def generate_date_dim(start_date, end_date) -> pd.DataFrame:
    df = pd.DataFrame({"date": pd.date_range(start=start_date, end=end_date, freq="D")})
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%B")
    df["quarter"] = "Q" + df["date"].dt.quarter.astype(str)
    df["day_of_week"] = df["date"].dt.day_name()
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["is_weekend"] = df["date"].dt.dayofweek >= 5
    return df


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    patients_df = generate_patients()
    providers_df = generate_providers()
    appointments_df = generate_appointments(patients_df, providers_df)
    treatments_df = generate_treatments(patients_df, appointments_df)
    date_dim_df = generate_date_dim(START_DATE, END_DATE)

    patients_df.to_csv(OUTPUT_DIR / "patients.csv", index=False)
    providers_df.to_csv(OUTPUT_DIR / "providers.csv", index=False)
    appointments_df.to_csv(OUTPUT_DIR / "appointments.csv", index=False)
    treatments_df.to_csv(OUTPUT_DIR / "treatments.csv", index=False)
    date_dim_df.to_csv(OUTPUT_DIR / "date_dim.csv", index=False)

    print("\nSynthetic oncology dataset created.")
    print(f"Output folder: {OUTPUT_DIR.resolve()}")
    print(f"Patients:      {len(patients_df):,}")
    print(f"Providers:     {len(providers_df):,}")
    print(f"Appointments:  {len(appointments_df):,}")
    print(f"Treatments:    {len(treatments_df):,}")

    print("\nTop diagnoses:")
    print(patients_df["primary_diagnosis"].value_counts().head(10))

    print("\nVenofer count:")
    print((treatments_df["regimen_name"] == "Venofer").sum())

    print("\nIDA patient count:")
    print((patients_df["primary_diagnosis"] == "Iron Deficiency Anemia").sum())


if __name__ == "__main__":
    main()