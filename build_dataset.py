from synthetic_data_generator.config import OUTPUT_DIR
from synthetic_data_generator.generate_appointments import generate_appointments
from synthetic_data_generator.generate_patients import generate_patients
from synthetic_data_generator.generate_providers import generate_providers
from synthetic_data_generator.generate_treatments import generate_treatments


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    patients_df = generate_patients()
    providers_df = generate_providers()
    appointments_df = generate_appointments(patients_df, providers_df)
    treatments_df = generate_treatments(patients_df, appointments_df)

    patients_df.to_csv(OUTPUT_DIR / "patients.csv", index=False)
    providers_df.to_csv(OUTPUT_DIR / "providers.csv", index=False)
    appointments_df.to_csv(OUTPUT_DIR / "appointments.csv", index=False)
    treatments_df.to_csv(OUTPUT_DIR / "treatments.csv", index=False)

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