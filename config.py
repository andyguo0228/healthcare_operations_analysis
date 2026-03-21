from datetime import date, timedelta
from pathlib import Path

SEED = 42

NUM_PATIENTS = 3600
NUM_PROVIDERS = 6

START_DATE = date.today() - timedelta(days=1095)
END_DATE = date.today()

OUTPUT_DIR = Path("synthetic_healthcare_data")

RACES = ["White", "Black", "Asian", "Hispanic", "Other"]
RACE_WEIGHTS = [35, 20, 18, 20, 7]

INSURANCE_TYPES = ["Commercial", "Medicare", "Medicaid", "Self-Pay"]

# Split the patient population between malignant oncology and benign hematology
DIAGNOSIS_GROUPS = {
    "malignant": 0.40,
    "ida": 0.60,
}

MALIGNANT_CANCERS = [
    "Breast Cancer",
    "Lung Cancer",
    "Colorectal Cancer",
    "Prostate Cancer",
    "Lymphoma",
    "Bladder Cancer",
    "Multiple Myeloma",
    "Ovarian Cancer",
    "Pancreatic Cancer",
]
MALIGNANT_WEIGHTS = [18, 16, 12, 13, 10, 8, 7, 6, 5]

VISIT_TYPES = [
    "New Patient",
    "Follow-up",
    "Infusion",
    "Lab Review",
    "Urgent Visit",
]
VISIT_TYPE_WEIGHTS = [8, 42, 26, 16, 8]

APPOINTMENT_STATUS = ["Completed", "No Show", "Cancelled"]
STATUS_WEIGHTS = [86, 7, 7]
