from datetime import date, timedelta
from pathlib import Path

SEED = 42

NUM_PATIENTS = 1200
NUM_PROVIDERS = 12

START_DATE = date.today() - timedelta(days=365)
END_DATE = date.today()

OUTPUT_DIR = Path("synthetic_oncology_data")

LOCATIONS = ["Rego Park", "Forest Hills", "Flushing", "Manhattan West"]
LOCATION_WEIGHTS = [40, 20, 20, 20]

EXAM_ROOMS = ["Exam Room 1", "Exam Room 2", "Exam Room 3", "Exam Room 4"]
INFUSION_CHAIRS = ["Infusion Chair A", "Infusion Chair B", "Infusion Chair C", "Infusion Chair D"]

RACES = ["White", "Black", "Asian", "Hispanic", "Other"]
RACE_WEIGHTS = [35, 20, 18, 20, 7]

ETHNICITIES = ["Non-Hispanic", "Hispanic or Latino"]
ETHNICITY_WEIGHTS = [78, 22]

INSURANCE_TYPES = ["Commercial", "Medicare", "Medicaid", "Self-Pay"]

PROVIDER_SPECIALTIES = [
    "Medical Oncology",
    "Hematology-Oncology",
    "Breast Oncology",
    "Thoracic Oncology",
]

# Split the patient population between malignant oncology and benign hematology
DIAGNOSIS_GROUPS = {
    "malignant": 0.92,
    "ida": 0.08,
}

MALIGNANT_CANCERS = [
    "Breast Cancer",
    "Lung Cancer",
    "Colorectal Cancer",
    "Prostate Cancer",
    "Lymphoma",
    "Leukemia",
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