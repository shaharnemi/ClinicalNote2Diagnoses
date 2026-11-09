"""HTTP API.

POST /predict            body: {"visit_id": "...", "note_text": "..."}
GET  /predict/{visit_id} predicts for a visit from data/visits.csv
GET  /health
"""
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src import config
from src.data import load_visits
from src.icd import load_icd
from src.model import BertEncoder, NearestProblemModel, suggest_codes

app = FastAPI(title="ClinicalNote2Diagnoses")
model = NearestProblemModel(BertEncoder()).load(config.MODEL_FILE)
billable, all_names = load_icd(config.ICD_XML)
visits = load_visits(config.VISITS_CSV)


class Visit(BaseModel):
    visit_id: Optional[str] = None
    note_text: str


def run(visit_id, note, min_score):
    return suggest_codes(model, visit_id, note, billable, all_names, min_score)


@app.get("/health")
def health():
    return {"status": "ok", "icd_release": config.ICD_RELEASE, "model": config.BERT_MODEL,
            "labelled_problems": len(model.texts)}


@app.post("/predict")
def predict(visit: Visit, min_score: float = config.MIN_SCORE):
    if not visit.note_text.strip():
        raise HTTPException(400, "note_text is empty")
    return run(visit.visit_id, visit.note_text, min_score)


@app.get("/predict/{visit_id}")
def predict_known_visit(visit_id: str, min_score: float = config.MIN_SCORE):
    if visit_id not in visits:
        raise HTTPException(404, f"unknown visit {visit_id}")
    return run(visit_id, visits[visit_id]["note_text"], min_score)
