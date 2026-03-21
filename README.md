# Healthcare Operations Analysis

This repository generates a synthetic outpatient oncology dataset for analytics, operations reporting, dashboard development, and workflow experimentation.

The project creates realistic-looking but fake data for:

- Patients
- Providers
- Appointments
- Treatments
- A date dimension

The generated data is intended for non-production use cases such as BI prototypes, SQL practice, capacity analysis, scheduling analysis, and operations modeling.

## What This Repo Does

Running the main build script creates a reproducible synthetic dataset for an outpatient oncology practice. The records include:

- Patient demographics, diagnosis mix, insurance, and treatment status
- Provider rosters with experience and FTE
- Appointment scheduling, patient flow paths, and clinic flow timestamps
- Treatment regimens, line of therapy, route, frequency, and intent
- A calendar table for time-based reporting

The default configuration models:

- 1,200 patients
- 12 providers
- A rolling 3-year date range ending on the run date
- Visit flows that move patients through waiting, lab, exam, infusion, and checkout states

## Repository Structure

- `build_dataset.py`: Main entrypoint that generates and exports all tables
- `config.py`: Central configuration for population size, date range, output path, and distributions
- `generate_patients.py`: Creates the patient dimension
- `generate_providers.py`: Creates the provider dimension
- `generate_appointments.py`: Creates appointment and clinic flow data
- `generate_treatments.py`: Creates treatment line and regimen data
- `utils.py`: Shared randomization, fake data, and helper utilities

## Requirements

This project uses Python 3.10+ and depends on:

- `pandas`
- `numpy`
- `faker`

You can install them with:

```bash
python3 -m pip install pandas numpy faker
```

## Quick Start

1. Install dependencies:

```bash
python3 -m pip install pandas numpy faker
```

1. Generate the dataset:

```bash
python3 build_dataset.py
```

1. Review the output in:

```bash
synthetic_healthcare_data/
```

## Output Files

The generator writes CSV files into `synthetic_healthcare_data/`:

- `patients.csv`
- `providers.csv`
- `appointments.csv`
- `treatments.csv`
- `date_dim.csv`

## Data Dictionary

Field-level data dictionaries are available in:

- `DATA_DICTIONARY.md` (human-readable)
- `DATA_DICTIONARY.csv` (machine-readable)

## Dataset Overview

### `patients.csv`

Contains one row per patient with fields such as:

- `patient_id`
- `mrn`
- `first_name`, `last_name`
- `sex`, `dob`, `age`
- `race`, `zip_code`
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
- `fte`

### `appointments.csv`

Contains one row per room-status event within an appointment (multiple rows per `appointment_id`) with scheduling and clinic flow metrics, including:

- `appointment_id`
- `patient_id`
- `mrn`
- `provider_id`
- `appointment_date`
- `room`
- `room_type`
- `room_datetime`
- `duration_min`
- `room_sequence`
- `patient_flow`
- `visit_type`
- `status`
- `scheduled_datetime`
- `check_in_datetime`
- `roomed_datetime`
- `provider_seen_datetime`
- `checkout_datetime`
- `arrival_delay_min`
- `wait_to_room_min`
- `wait_to_provider_min`
- `provider_cycle_min`
- `visit_duration_min`
- `total_los_min`
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

### `date_dim.csv`

Contains a reporting calendar dimension with:

- `date`
- `year`
- `month`
- `month_name`
- `quarter`
- `day_of_week`
- `week_of_year`
- `is_weekend`

## Data Generation Logic

The synthetic data is designed to loosely reflect common oncology operations patterns:

- Patients are mostly malignant oncology, with a smaller iron deficiency anemia population
- Diagnosis-specific logic influences sex mix, stage/risk, smoking status, and treatment likelihood
- Providers are assigned across visits without specialty or location constraints
- Visit counts vary by diagnosis, acuity, and active treatment status
- Infusion visits generally have longer operational timelines than office visits
- Follow-up and infusion visits move through explicit room/state sequences
- Treatment regimens, routes, duration, and intent vary by diagnosis and stage/risk

Randomness is seeded in `utils.py` via `config.SEED`, so repeated runs with the same configuration are reproducible.

## Customization

You can tune the generated dataset by editing `config.py`. Common changes include:

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
- Dates are relative to the day the generator is run unless you change `config.py`
- Each row in `appointments.csv` is a single room-status event; completed visits have multiple rows per appointment
- `room` may include specific physical room labels like `Exam Rm 3` and `Infusion Bay 8`

## Current Local Verification

The main script was invoked locally with:

```bash
python3 build_dataset.py
```

That run failed because `faker` is not currently installed in the environment. After installing dependencies, the same command should generate the CSV outputs described above.
