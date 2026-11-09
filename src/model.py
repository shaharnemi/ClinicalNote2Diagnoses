"""Nearest labelled problem, using a Hebrew BERT (DictaBERT).

Training: split every annotated note into problems and give each problem its
code (the doctors code problems in note order). Embed the problems with BERT.
Prediction: split the new note the same way, and for each problem copy the
code of the most similar training problem. The cosine similarity is the score.

Run `python -m src.model` to download BERT, fit on all annotated visits and
save the result to cache/model.npz (the API loads that file).
"""
import os

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from src import config
from src.data import codes_in_note_order, load_annotations, load_visits, majority_labels
from src.icd import check_code, load_icd
from src.notes import find_boilerplate, split_problems


class BertEncoder:
    def __init__(self, model_name=config.BERT_MODEL):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).eval()
        self.cache = {}  # the same problems come back in every CV fold

    def encode(self, texts, batch_size=32):
        missing = [t for t in dict.fromkeys(texts) if t not in self.cache]
        for i in range(0, len(missing), batch_size):
            batch = missing[i:i + batch_size]
            tokens = self.tokenizer(batch, padding=True, truncation=True, max_length=128, return_tensors="pt")
            with torch.no_grad():
                hidden = self.model(**tokens).last_hidden_state
            # mean of the token vectors, ignoring padding
            mask = tokens["attention_mask"].unsqueeze(-1)
            vectors = (hidden * mask).sum(1) / mask.sum(1)
            vectors = torch.nn.functional.normalize(vectors, dim=1).numpy()
            self.cache.update(zip(batch, vectors))
        return np.array([self.cache[t] for t in texts])


class NearestProblemModel:
    def __init__(self, encoder):
        self.encoder = encoder
        self.boilerplate = set()
        self.texts, self.codes, self.visit_ids = [], [], []
        self.vectors = None

    def fit(self, all_notes, notes, annotations, gold):
        """all_notes: every note (only used to find repeated filler lines).
        notes: {visit_id: note} for the visits we learn from."""
        self.boilerplate = find_boilerplate(all_notes)
        self.texts, self.codes, self.visit_ids = [], [], []
        for visit_id, note in notes.items():
            problems = split_problems(note, self.boilerplate)
            codes = codes_in_note_order(annotations, gold, visit_id)
            if len(problems) != len(codes):
                continue  # doctors disagreed on a problem, can't tell which code is which
            for lines, code in zip(problems, codes):
                self.texts.append(" ".join(lines))
                self.codes.append(code)
                self.visit_ids.append(visit_id)
        self.vectors = self.encoder.encode(self.texts)
        return self

    def predict(self, note, min_score=0.0):
        problems = split_problems(note, self.boilerplate)
        if not problems:
            return []
        vectors = self.encoder.encode([" ".join(p) for p in problems])
        best = {}
        for lines, vector in zip(problems, vectors):
            sims = self.vectors @ vector
            i = int(sims.argmax())
            score = round(float(sims[i]), 3)
            code = self.codes[i]
            if score < min_score or (code in best and best[code]["score"] >= score):
                continue
            best[code] = {
                "code": code,
                "score": score,
                "evidence": self._evidence(lines, i),
                "similar_visit": self.visit_ids[i],
            }
        return sorted(best.values(), key=lambda p: -p["score"])

    def _evidence(self, lines, train_index):
        """The line of the problem that is closest to the matched training problem."""
        if len(lines) == 1:
            return lines[0]
        sims = self.encoder.encode(lines) @ self.vectors[train_index]
        return lines[int(sims.argmax())]

    def save(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        np.savez(path, texts=self.texts, codes=self.codes, visit_ids=self.visit_ids,
                 vectors=self.vectors, boilerplate=sorted(self.boilerplate))

    def load(self, path):
        data = np.load(path)
        self.texts, self.codes, self.visit_ids = ([str(x) for x in data[k]] for k in ("texts", "codes", "visit_ids"))
        self.vectors = data["vectors"]
        self.boilerplate = {str(x) for x in data["boilerplate"]}
        return self


def add_descriptions(predictions, billable, all_names):
    """Code names come from the ICD-10-CM XML. Codes that are not valid final
    codes in this release are flagged instead of hidden."""
    for p in predictions:
        status = check_code(p["code"], billable, all_names)
        if status == "ok":
            p["description"] = billable[p["code"]]["desc"]
        else:
            p["description"] = all_names.get(p["code"], "")
            p["warning"] = ("category code, a more specific code exists in FY2027" if status == "not_final"
                            else "not a valid ICD-10-CM FY2027 code")
    return predictions


def suggest_codes(model, visit_id, note, billable, all_names, min_score=config.MIN_SCORE):
    """The answer the API returns. Matches below min_score are not given as
    codes, they are listed under "not_coded" so a clinician can see which
    problems still need a code."""
    found = add_descriptions(model.predict(note), billable, all_names)
    return {
        "visit_id": visit_id,
        "predictions": [p for p in found if p["score"] >= min_score],
        "not_coded": [{"evidence": p["evidence"], "closest_code": p["code"], "score": p["score"]}
                      for p in found if p["score"] < min_score],
    }


def train_full_model():
    visits = load_visits(config.VISITS_CSV)
    annotations = load_annotations(config.ANNOTATIONS_CSV)
    gold = majority_labels(annotations)
    model = NearestProblemModel(BertEncoder())
    model.fit([v["note_text"] for v in visits.values()],
              {v: visits[v]["note_text"] for v in gold}, annotations, gold)
    return model


if __name__ == "__main__":
    model = train_full_model()
    model.save(config.MODEL_FILE)
    print(f"saved {len(model.texts)} labelled problems to {config.MODEL_FILE}")
