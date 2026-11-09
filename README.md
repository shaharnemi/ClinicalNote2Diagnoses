# ClinicalNote2Diagnoses

Small POC that suggests ICD-10-CM codes for a Hebrew clinical visit note, with a
score and the line from the note that supports each code.

ICD-10-CM release used: **FY2027 (October 1, 2026)**, CDC/NCHS tabular XML
(`icd10cm-tabular-2027.xml` from `icd10cm-table-and-index-2027.zip`,
https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2027/).
FY2027 is the release that covers the visit dates in the data (Oct 2026 - Sep 2027).

## Running

```bash
docker compose up --build
```

The first build downloads Python packages and the DictaBERT model (~2 GB image)
and fits the model. After that the container runs without internet.
The API is on http://localhost:8000 (Swagger UI at `/docs`).
If port 8000 is taken, pick another one: `API_PORT=8010 docker compose up --build`.

```bash
# a visit from visits.csv
curl http://localhost:8000/predict/V0041

# any note
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"visit_id": "X1", "note_text": "ביקור מרפאתי. בת 30.\nמתאר/ת כי צריבה ותכיפות במתן שתן מזה יומיים."}'
```

Example answer:

```json
{
  "visit_id": "V0041",
  "predictions": [
    {"code": "I30.9", "score": 1.0, "evidence": "כאב חד בחזה שמתגבר בשכיבה ומשתפר בישיבה קדימה.",
     "similar_visit": "V0266", "description": "Acute pericarditis, unspecified"},
    {"code": "J43.9", "score": 1.0, "evidence": "CT מציג שינויים אמפיזמטוטיים.",
     "similar_visit": "V0140", "description": "Emphysema, unspecified"}
  ],
  "not_coded": [
    {"evidence": "נפיחות חד צדדית וכאב בשוק אחרי חוסר ניידות.", "closest_code": "K80.20", "score": 0.886}
  ]
}
```

- `similar_visit` is the annotated visit the code was copied from.
- `not_coded` lists problems with no close enough match, so a clinician can see what is still missing (here the DVT: no other visit has it).
- `min_score` (default 0.95) can be changed per request: `/predict/V0041?min_score=0`.
- The API model is trained on all 510 annotated visits, so asking about one of them mostly finds the visit itself. The honest numbers are the cross-validation ones below.

Evaluation and tests (inside the image, results are written to `./results`):

```bash
docker compose run --rm api python -m src.evaluate
docker compose run --rm api python -m pytest -q tests
```

Predictions for the 90 visits without annotations (`results/predictions_unlabelled.json`):

```bash
docker compose run --rm api python -m src.predict_unlabelled
```

84 of their problems got a code and 72 were left as `not_coded` (23 visits fully
coded, 36 with nothing coded). That is in line with the cross validation: about
half the problems have a similar annotated problem to copy from.

## Code

| file | what it does |
|---|---|
| `src/notes.py` | splits a note into problems, removes header / filler lines and openers like "בבדיקה:" |
| `src/data.py` | loads the CSVs, majority labels, codes in note order |
| `src/model.py` | DictaBERT embeddings + nearest labelled problem |
| `src/icd.py` | reads the ICD-10-CM XML (names, valid final codes, 7th character) |
| `src/evaluate.py` | cross validation and the report in `results/` |
| `src/predict_unlabelled.py` | predictions for the 90 visits without annotations |
| `src/api.py` | FastAPI app |

## My approach

When I first looked at the data, I saw that all the summaries follow the same logic: the type of visit, gender and age, then a few diagnostic findings and symptoms, and at the end some general sentences about the treatment plan. A new issue usually starts with a fixed phrase such as "another subject..." ("נושא נוסף...").

The doctors wrote the codes in the same order as the issues appear in the visit summary. Some lines repeat in several summaries, and they almost always got the same code.

My approach was to split each summary into issues. Each issue is turned into a vector with DictaBERT, and a new issue gets the code of the most similar issue that was already coded.

I tried a few other approaches: AlephBERT, a multilingual model (multilingual-e5) and simple TF-IDF. They all got about the same result. I also tried translating the issues to English and searching the ICD XML, but it found the right code first in only about 13% of the cases, so I didn't use it.

Because this is a medical setting, a false positive (a wrong code) is worse than a false negative (no code). So I decided that an issue with a score below 0.95 is marked as unknown instead of getting a code that might be wrong.

The limitation comes from the data and not from the model: issues whose code has no example in the annotated visits can't be found, and they are mostly marked as unknown. This also shows in `predictions_unlabelled.json`, where almost 50% of the issues are unknown.

## Evaluation

5-fold cross validation over the 510 annotated visits (the 90 without labels
can't be scored). Reference = codes given by at least 2 of the 3 doctors. Full
tables are in [results/report.md](results/report.md), mistakes in
`results/errors.csv`.

| | precision | recall | F1 |
|---|---|---|---|
| all suggestions | 0.50 | 0.52 | 0.51 |
| score >= 0.95 (API default) | 0.97 | 0.51 | 0.67 |
| doctors, each vs. the other two | 0.88-0.94 | 0.93-0.98 | ~0.93 |

What the numbers say:

- **Half of the codes can't be reached.** 48% of the codes in a test fold never
  appear in the training folds. For codes it has seen, recall is 99.5%; for the
  rest it is 0. Most of the gap from the doctors is this.
- **The score is useful.** Above 0.95 almost every suggestion is right (97%),
  below 0.90 almost none is. So low scores are returned as "not coded" instead
  of a wrong code.
- The 0.95 cut was chosen on the same cross-validation results, so it is a bit
  optimistic.
- Specialties with rare codes (oncology, ophthalmology, nephrology) score worst.

Label quality (also in the report):

- The doctors fully agree on 409/510 visits; most disagreements are about the 2nd/3rd problem.
- `M13.9` (11 rows) is not an ICD-10-CM code (it is from WHO ICD-10). The CM code would be `M19.90`.
- `G35`, `I31.3`, `I42.0`, `I47.1`, `M72.2`, `R76.8` are categories in FY2027 with more specific sub-codes, so the doctors probably used an older release.
- In 2 visits the doctors skipped a problem entirely (e.g. V0047, the tachycardia).
- The API returns these codes as the doctors gave them, with a `warning`.

## Assumptions and limitations

- The notes have a fixed structure (one opener per new problem). Splitting into
  problems depends on it and matches the number of codes in 508/510 visits.
  Free-text notes from real life would need a smarter split.
- The doctors code problems in note order. I used that to pair each problem
  with its code (checked: a line that repeats between notes gets the same code
  395 times out of 396).
- Only codes that appear in the 510 annotated visits can be suggested. The ICD
  XML is used for names and validation, not for finding new codes.
- One code per problem. Combination codes / secondary codes are not handled.
- 7th character: when "A" (initial encounter) exists only that one is listed.
- DictaBERT is used as is (mean pooling, no fine-tuning). I also tried AlephBERT,
  multilingual-e5 and plain TF-IDF character n-grams: all gave F1 ~0.51,
  because the ceiling is the unseen codes, not the encoder.

## Next steps

- Reach unseen codes: translate the problem to English (offline MarianMT
  he->en) and search the ICD descriptions. In a quick test this found the right
  code first in only ~13% of cases, so it would need reranking before it helps.
- Fine-tune BERT on (problem, code) pairs when there is more labelled data.
