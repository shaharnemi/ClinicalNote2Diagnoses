"""Loading the visits and the physician annotations."""
import csv
from collections import Counter, defaultdict


def load_visits(path):
    with open(path, encoding="utf-8-sig") as f:
        return {row["visit_id"]: row for row in csv.DictReader(f)}


def load_annotations(path):
    """{visit_id: {annotator_id: [codes in the order they were recorded]}}"""
    with open(path, encoding="utf-8-sig") as f:
        rows = sorted(csv.DictReader(f), key=lambda r: int(r["annotation_rank"]))
    out = defaultdict(lambda: defaultdict(list))
    for r in rows:
        out[r["visit_id"]][r["annotator_id"]].append(r["icd10cm_code"].strip())
    return {v: dict(d) for v, d in out.items()}


def majority_labels(annotations, min_votes=2):
    """A code is in the reference if at least `min_votes` of the 3 doctors gave it."""
    gold = {}
    for visit_id, by_doctor in annotations.items():
        votes = Counter(code for codes in by_doctor.values() for code in set(codes))
        gold[visit_id] = {code for code, n in votes.items() if n >= min_votes}
    return gold


def codes_in_note_order(annotations, gold, visit_id):
    """Majority codes sorted by the order the doctors typed them.

    The doctors code the problems in the order they appear in the note, so the
    first code belongs to the first problem and so on (checked on the data:
    lines that repeat between notes almost always get the same code this way).
    """
    positions = defaultdict(list)
    for codes in annotations[visit_id].values():
        for i, code in enumerate(codes):
            positions[code].append(i)
    return sorted(gold[visit_id], key=lambda c: sum(positions[c]) / len(positions[c]))
