"""Paths and settings. Everything can be overridden with environment variables."""
import os

DATA_DIR = os.getenv("DATA_DIR", "data")
ICD_XML = os.getenv("ICD_XML", f"{DATA_DIR}/icd10cm-tabular-2027.xml")
ICD_RELEASE = "ICD-10-CM FY2027 (October 1, 2026), CDC/NCHS tabular XML"
VISITS_CSV = os.getenv("VISITS_CSV", f"{DATA_DIR}/visits.csv")
ANNOTATIONS_CSV = os.getenv("ANNOTATIONS_CSV", f"{DATA_DIR}/physician_annotations.csv")

BERT_MODEL = os.getenv("BERT_MODEL", "dicta-il/dictabert")
MODEL_FILE = os.getenv("MODEL_FILE", "cache/model.npz")
RESULTS_DIR = os.getenv("RESULTS_DIR", "results")
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.95"))  # picked from results/report.md
