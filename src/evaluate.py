"""Evaluation with 5-fold cross validation over the 510 annotated visits.

Run:  python -m src.evaluate
Writes results/metrics.json, results/report.md and results/errors.csv
"""
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from src import config
from src.data import load_annotations, load_visits, majority_labels
from src.icd import check_code, load_icd
from src.model import BertEncoder, NearestProblemModel

FOLDS = 5
SEED = 42
DOCTORS = ("DR_A", "DR_B", "DR_C")
METRICS = ["precision", "recall", "f1", "exact_visit"]


def prf(pairs):
    """pairs: list of (predicted set, reference set). Micro precision/recall/F1."""
    tp = sum(len(p & g) for p, g in pairs)
    n_pred = sum(len(p) for p, _ in pairs)
    n_gold = sum(len(g) for _, g in pairs)
    precision = tp / n_pred if n_pred else 0.0
    recall = tp / n_gold if n_gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    exact = sum(p == g for p, g in pairs) / len(pairs) if pairs else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
            "exact_visit": round(exact, 3), "visits": len(pairs)}


def to_category(pairs):
    """Same pairs, but only the 3-character category (E11.319 -> E11)."""
    cut = lambda codes: {c.split(".")[0] for c in codes}
    return [(cut(p), cut(g)) for p, g in pairs]


def split_folds(visit_ids):
    ids = sorted(visit_ids)
    random.Random(SEED).shuffle(ids)
    return [ids[i::FOLDS] for i in range(FOLDS)]


def cross_validate(model, visits, annotations, gold):
    """Every annotated visit is predicted by a model that did not see it."""
    all_notes = [v["note_text"] for v in visits.values()]
    predictions, train_codes = {}, {}
    for fold in split_folds(gold):
        test = set(fold)
        train = {v: visits[v]["note_text"] for v in gold if v not in test}
        model.fit(all_notes, train, annotations, gold)
        seen = set(model.codes)
        for v in fold:
            predictions[v] = model.predict(visits[v]["note_text"])
            train_codes[v] = seen
    return predictions, train_codes


def codes_of(preds, min_score=0.0):
    return {p["code"] for p in preds if p["score"] >= min_score}


def seen_vs_unseen(predictions, train_codes, gold):
    """A nearest-neighbour model can only give codes it has seen in training,
    so recall is split by that, and the share of seen codes is the ceiling."""
    counts = Counter()
    for v, codes in gold.items():
        predicted = codes_of(predictions[v])
        for c in codes:
            group = "seen in training" if c in train_codes[v] else "never seen in training"
            counts[group, "n"] += 1
            counts[group, "hit"] += c in predicted
    out = {}
    for group in ("seen in training", "never seen in training"):
        n = counts[group, "n"]
        out[group] = {"codes": n, "share": round(n / sum(len(g) for g in gold.values()), 3),
                      "recall": round(counts[group, "hit"] / n, 3) if n else None}
    return out


def human_agreement(annotations):
    """Each doctor against the codes the other two both gave."""
    out = {}
    for doc in DOCTORS:
        a, b = [d for d in DOCTORS if d != doc]
        pairs = [(set(x.get(doc, [])), set(x.get(a, [])) & set(x.get(b, []))) for x in annotations.values()]
        out[doc] = prf(pairs)
    return out


def model_vs_doctor_pairs(predictions, annotations):
    """The model against the same 'other two agree' references."""
    out = {}
    for doc in DOCTORS:
        a, b = [d for d in DOCTORS if d != doc]
        pairs = [(codes_of(predictions[v]), set(x.get(a, [])) & set(x.get(b, []))) for v, x in annotations.items()]
        out[f"model vs {a}+{b}"] = prf(pairs)
    return out


def score_buckets(predictions, gold, edges=(0.0, 0.85, 0.9, 0.95, 0.98, 1.01)):
    """Is a higher score really more often correct?"""
    flat = [(p["score"], p["code"] in gold[v]) for v, ps in predictions.items() for p in ps]
    rows = []
    for lo, hi in zip(edges, edges[1:]):
        hits = [ok for s, ok in flat if lo <= s < hi]
        if hits:
            rows.append({"score": f"{lo:.2f}-{min(hi, 1.0):.2f}", "predictions": len(hits),
                         "precision": round(sum(hits) / len(hits), 3)})
    return rows


def by_field(predictions, gold, visits, field):
    groups = defaultdict(list)
    for v in gold:
        groups[visits[v][field]].append((codes_of(predictions[v]), gold[v]))
    return {k: prf(pairs) for k, pairs in sorted(groups.items(), key=lambda kv: -len(kv[1]))}


def label_quality(annotations, gold, billable, all_names):
    rows = Counter()
    bad = defaultdict(set)
    for by_doc in annotations.values():
        for codes in by_doc.values():
            for c in codes:
                status = check_code(c, billable, all_names)
                rows[status] += 1
                if status != "ok":
                    bad[status].add(c)
    all_agree = sum(len({tuple(sorted(c)) for c in a.values()}) == 1 for a in annotations.values())
    return {"annotation_rows_by_status": dict(rows),
            "not_in_release": sorted(bad["unknown"]),
            "category_not_final": sorted(bad["not_final"]),
            "visits_all_three_identical": all_agree,
            "visits": len(annotations)}


def write_errors(path, predictions, gold, visits):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["visit_id", "specialty", "gold", "predicted", "missed", "extra", "scores", "note"])
        for v in sorted(gold):
            pred = codes_of(predictions[v])
            if pred != gold[v]:
                scores = " ".join(f"{p['code']}:{p['score']}" for p in predictions[v])
                w.writerow([v, visits[v]["physician_specialty"], " ".join(sorted(gold[v])), " ".join(sorted(pred)),
                            " ".join(sorted(gold[v] - pred)), " ".join(sorted(pred - gold[v])), scores,
                            visits[v]["note_text"].replace("\n", " / ")])


def md_table(rows, columns):
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(str(r.get(c, "")) for c in columns) + " |" for r in rows]
    return "\n".join(lines)


def write_report(path, r):
    parts = [
        "# Evaluation results\n",
        f"{FOLDS}-fold cross validation on the 510 annotated visits. Model: `{r['model']}`, "
        f"ICD release: {r['icd_release']}. Reference = codes given by at least 2 of the 3 doctors.\n",
        "## Main numbers\n",
        md_table([{"level": "full code", **r["code_level"]}, {"level": "3-char category", **r["category_level"]},
                  {"level": "full code, any doctor's code counts", **r["vs_any_doctor"]}], ["level"] + METRICS),
        "\n## Seen vs. never seen codes\n",
        md_table([{"group": k, **v} for k, v in r["seen_vs_unseen"].items()], ["group", "codes", "share", "recall"]),
        "\n## Compared with the doctors\n\nEach doctor against the codes the other two agreed on, "
        "and the model against the same references.\n",
        md_table([{"who": k, **v} for k, v in {**r["doctors"], **r["model_vs_doctor_pairs"]}.items()], ["who"] + METRICS),
        "\n## Does the score mean something?\n",
        md_table(r["score_buckets"], ["score", "predictions", "precision"]),
        "\nOnly keeping predictions above a score:\n",
        md_table([{"min score": k, **v} for k, v in r["thresholds"].items()], ["min score"] + METRICS),
        "\n## By visit type\n",
        md_table([{"visit type": k, **v} for k, v in r["by_visit_type"].items()], ["visit type", "visits"] + METRICS),
        "\n## By specialty\n",
        md_table([{"specialty": k, **v} for k, v in r["by_specialty"].items()], ["specialty", "visits"] + METRICS),
        "\n## Label quality\n",
        "```\n" + json.dumps(r["label_quality"], indent=2) + "\n```\n",
    ]
    Path(path).write_text("\n".join(parts), encoding="utf-8")


def main():
    out = Path(config.RESULTS_DIR)
    out.mkdir(exist_ok=True)
    visits = load_visits(config.VISITS_CSV)
    annotations = load_annotations(config.ANNOTATIONS_CSV)
    gold = majority_labels(annotations)
    billable, all_names = load_icd(config.ICD_XML)

    model = NearestProblemModel(BertEncoder())
    predictions, train_codes = cross_validate(model, visits, annotations, gold)
    pairs = [(codes_of(predictions[v]), gold[v]) for v in gold]
    any_doctor = {v: {c for codes in a.values() for c in codes} for v, a in annotations.items()}

    r = {
        "model": config.BERT_MODEL,
        "icd_release": config.ICD_RELEASE,
        "code_level": prf(pairs),
        "category_level": prf(to_category(pairs)),
        "vs_any_doctor": prf([(codes_of(predictions[v]), any_doctor[v]) for v in gold]),
        "seen_vs_unseen": seen_vs_unseen(predictions, train_codes, gold),
        "doctors": human_agreement(annotations),
        "model_vs_doctor_pairs": model_vs_doctor_pairs(predictions, annotations),
        "score_buckets": score_buckets(predictions, gold),
        "thresholds": {str(t): prf([(codes_of(predictions[v], t), gold[v]) for v in gold])
                       for t in (0.0, 0.9, 0.95, 0.98)},
        "by_visit_type": by_field(predictions, gold, visits, "visit_type"),
        "by_specialty": by_field(predictions, gold, visits, "physician_specialty"),
        "label_quality": label_quality(annotations, gold, billable, all_names),
    }
    (out / "metrics.json").write_text(json.dumps(r, indent=2, ensure_ascii=False))
    write_errors(out / "errors.csv", predictions, gold, visits)
    write_report(out / "report.md", r)
    print((out / "report.md").read_text())


if __name__ == "__main__":
    main()
