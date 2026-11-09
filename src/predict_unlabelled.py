"""Predictions for the 90 visits the doctors did not annotate.

Run:  python -m src.predict_unlabelled
Writes results/predictions_unlabelled.json
"""
import json
import os
from collections import Counter
from pathlib import Path

from src import config
from src.data import load_annotations, load_visits
from src.icd import load_icd
from src.model import BertEncoder, NearestProblemModel, suggest_codes, train_full_model


def main():
    if os.path.exists(config.MODEL_FILE):
        model = NearestProblemModel(BertEncoder()).load(config.MODEL_FILE)
    else:
        model = train_full_model()
    billable, all_names = load_icd(config.ICD_XML)
    visits = load_visits(config.VISITS_CSV)
    annotated = load_annotations(config.ANNOTATIONS_CSV)

    unlabelled = sorted(v for v in visits if v not in annotated)
    results = [suggest_codes(model, v, visits[v]["note_text"], billable, all_names) for v in unlabelled]

    out = Path(config.RESULTS_DIR)
    out.mkdir(exist_ok=True)
    (out / "predictions_unlabelled.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    coded = sum(len(r["predictions"]) for r in results)
    not_coded = sum(len(r["not_coded"]) for r in results)
    fully = sum(1 for r in results if r["predictions"] and not r["not_coded"])
    nothing = sum(1 for r in results if not r["predictions"])
    print(f"{len(results)} visits: {coded} problems coded, {not_coded} left as not_coded")
    print(f"all problems coded: {fully} visits, nothing coded: {nothing} visits")
    print("most common codes:", Counter(p["code"] for r in results for p in r["predictions"]).most_common(5))


if __name__ == "__main__":
    main()
