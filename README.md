# Healthcare Operations Analysis

This repository generates a synthetic outpatient oncology dataset for analytics, operations reporting, dashboard development, and workflow experimentation.

The project creates realistic-looking but fake data for:

- Patients
- Providers
- Appointments
- Treatments

The generated data is intended for non-production use cases such as BI prototypes, SQL practice, capacity analysis, scheduling analysis, and operations modeling.

## What This Repo Does

Running the main build script creates a reproducible synthetic dataset for an outpatient oncology practice. The records include:

- Patient demographics, diagnosis mix, insurance, and treatment status
- Provider rosters with provider identity and years of experience
- Appointment scheduling, patient flow paths, and room event timestamps/durations
- Treatment regimens, line of therapy, route, frequency, and intent

The default configuration models:

- 4,000-5,000 patients (randomized per run, seeded)
- 8 providers
- A rolling 3-year date range ending on the run date
- Visit flows that move patients through waiting, lab, exam, infusion, and checkout states

## Repository Structure

- `build_dataset.py`: Main entrypoint that generates and exports all tables
- `synthetic_data_generator/config.py`: Central configuration for population size, date range, output path, and distributions
- `synthetic_data_generator/generate_patients.py`: Creates the patient dimension
- `synthetic_data_generator/generate_providers.py`: Creates the provider dimension
- `synthetic_data_generator/generate_appointments.py`: Creates appointment and clinic flow data
- `synthetic_data_generator/generate_treatments.py`: Creates treatment line and regimen data
- `synthetic_data_generator/utils.py`: Shared randomization, fake data, and helper utilities

## Requirements

This project uses Python 3.10+ and depends on:

- `pandas`
- `numpy`
- `faker`

You can install them with:

```bash
python -m pip install pandas numpy faker
```

## Quick Start

1. Install dependencies:

```bash
python -m pip install pandas numpy faker
```

2. Generate the dataset:

```bash
python build_dataset.py
```

3. Review the output in:

```bash
data/
```

## Output Files

The generator writes CSV files into `data/`:

- `patients.csv`
- `providers.csv`
- `appointments.csv`
- `treatments.csv`

## Data Dictionary

Field-level data dictionaries are available in:

- `DATA_DICTIONARY.md` (human-readable)
- `DATA_DICTIONARY.csv` (machine-readable)

Validate that generated CSV headers match the dictionary:

```bash
python validate_schema.py
```

Optional custom paths:

```bash
python validate_schema.py --dictionary DATA_DICTIONARY.csv --data-dir data
```

## Dataset Overview

### `patients.csv`

Contains one row per patient with fields such as:

- `patient_id`
- `mrn`
- `first_name`, `last_name`
- `sex`, `dob`, `age`
- `zip_code`
- `insurance_type`
- `diagnosis_group`
- `primary_diagnosis`
- `stage`
- `comorbidity_score`
- `smoking_status`
- `active_treatment_flag`
- `deceased_flag`

### `providers.csv`

Contains one row per provider with fields such as:

- `provider_id`
- `provider_name`
- `years_experience`

### `appointments.csv`

Contains one row per room-status event within an appointment (multiple rows per `appointment_id`) with event-level clinic flow metrics, including:

- `appointment_id`
- `mrn`
- `provider_id`
- `appointment_date`
- `room`
- `room_type`
- `room_timestamp`
- `duration`
- `visit_type`
- `status`
- `new_patient_flag`
- `infusion_flag`
- `urgent_flag`

### `treatments.csv`

Contains treatment-line data with fields such as:

- `treatment_id`
- `patient_id`
- `line_of_therapy`
- `regimen_name`
- `treatment_category`
- `route`
- `frequency`
- `intent`
- `start_date`
- `end_date`
- `active_flag`

## Data Generation Logic

The synthetic data is designed to loosely reflect common oncology operations patterns:

- Patients are split across malignant oncology and iron deficiency anemia populations
- Diagnosis-specific logic influences sex mix, stage/risk, smoking status, and treatment likelihood
- Providers are assigned across visits without specialty or location constraints
- Visit counts vary by diagnosis, acuity, and active treatment status
- Infusion visits generally have longer operational timelines than office visits
- Follow-up and infusion visits move through explicit room/state sequences
- Treatment regimens, routes, duration, and intent vary by diagnosis and stage/risk

Randomness is seeded in `synthetic_data_generator/utils.py` via `config.SEED`, so repeated runs with the same configuration are reproducible.

## Customization

You can tune the generated dataset by editing `synthetic_data_generator/config.py`. Common changes include:

- `NUM_PATIENTS`
- `NUM_PROVIDERS`
- `START_DATE`
- `END_DATE`
- `OUTPUT_DIR`
- Diagnosis distributions
- Visit type and appointment status weights

## Example Use Cases

- Build a Power BI or Tableau operations dashboard
- Practice SQL joins, aggregations, and cohort analysis
- Model clinic throughput and patient movement through care areas
- Analyze no-show and cancellation patterns
- Explore provider productivity and throughput
- Test healthcare analytics pipelines without PHI

## Notes

- All data is synthetic and generated with fake names and identifiers
- The dataset is not suitable for clinical, billing, or compliance use
- Dates are relative to the day the generator is run unless you change `synthetic_data_generator/config.py`
- Each row in `appointments.csv` is a single room-status event; completed visits have multiple rows per appointment
- `room` may include specific physical room labels like `Exam Rm 3` and `Infusion Bay 8`
