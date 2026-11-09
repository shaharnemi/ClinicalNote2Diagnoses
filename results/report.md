# Evaluation results

5-fold cross validation on the 510 annotated visits. Model: `dicta-il/dictabert`, ICD release: ICD-10-CM FY2027 (October 1, 2026), CDC/NCHS tabular XML. Reference = codes given by at least 2 of the 3 doctors.

## Main numbers

| level | precision | recall | f1 | exact_visit |
|---|---|---|---|---|
| full code | 0.504 | 0.517 | 0.51 | 0.327 |
| 3-char category | 0.543 | 0.556 | 0.549 | 0.369 |
| full code, any doctor's code counts | 0.515 | 0.516 | 0.515 | 0.335 |

## Seen vs. never seen codes

| group | codes | share | recall |
|---|---|---|---|
| seen in training | 402 | 0.519 | 0.995 |
| never seen in training | 372 | 0.481 | 0.0 |

## Compared with the doctors

Each doctor against the codes the other two agreed on, and the model against the same references.

| who | precision | recall | f1 | exact_visit |
|---|---|---|---|---|
| DR_A | 0.876 | 0.98 | 0.925 | 0.81 |
| DR_B | 0.905 | 0.96 | 0.932 | 0.825 |
| DR_C | 0.939 | 0.926 | 0.933 | 0.825 |
| model vs DR_B+DR_C | 0.426 | 0.488 | 0.455 | 0.259 |
| model vs DR_A+DR_C | 0.44 | 0.494 | 0.465 | 0.276 |
| model vs DR_A+DR_B | 0.465 | 0.504 | 0.484 | 0.296 |

## Does the score mean something?

| score | predictions | precision |
|---|---|---|
| 0.00-0.85 | 59 | 0.0 |
| 0.85-0.90 | 243 | 0.0 |
| 0.90-0.95 | 88 | 0.091 |
| 0.95-0.98 | 75 | 0.947 |
| 0.98-1.00 | 329 | 0.976 |

Only keeping predictions above a score:

| min score | precision | recall | f1 | exact_visit |
|---|---|---|---|---|
| 0.0 | 0.504 | 0.517 | 0.51 | 0.327 |
| 0.9 | 0.813 | 0.517 | 0.632 | 0.337 |
| 0.95 | 0.97 | 0.506 | 0.666 | 0.327 |
| 0.98 | 0.976 | 0.415 | 0.582 | 0.235 |

## By visit type

| visit type | visits | precision | recall | f1 | exact_visit |
|---|---|---|---|---|---|
| new | 335 | 0.493 | 0.506 | 0.5 | 0.328 |
| follow_up | 148 | 0.558 | 0.575 | 0.566 | 0.358 |
| urgent | 27 | 0.348 | 0.348 | 0.348 | 0.148 |

## By specialty

| specialty | visits | precision | recall | f1 | exact_visit |
|---|---|---|---|---|---|
| Family Medicine | 159 | 0.647 | 0.672 | 0.659 | 0.384 |
| Orthopedics and Rehabilitation | 30 | 0.636 | 0.636 | 0.636 | 0.567 |
| Dermatology | 29 | 0.513 | 0.513 | 0.513 | 0.448 |
| Gastroenterology and Hepatology | 26 | 0.395 | 0.417 | 0.405 | 0.231 |
| Pulmonology | 24 | 0.552 | 0.571 | 0.561 | 0.542 |
| Injuries, Accidents and Acute Care | 24 | 0.385 | 0.385 | 0.385 | 0.167 |
| Gynecology and Obstetrics | 22 | 0.323 | 0.345 | 0.333 | 0.136 |
| Other Clinical Presentations | 20 | 0.0 | 0.0 | 0.0 | 0.0 |
| Nephrology and Urology | 20 | 0.136 | 0.136 | 0.136 | 0.1 |
| ENT and Audiology | 19 | 0.35 | 0.35 | 0.35 | 0.316 |
| Oncology and Neoplasms | 19 | 0.0 | 0.0 | 0.0 | 0.0 |
| Infectious Disease | 16 | 0.5 | 0.5 | 0.5 | 0.438 |
| Endocrinology and Metabolic | 15 | 0.737 | 0.778 | 0.757 | 0.733 |
| Rheumatology | 15 | 0.444 | 0.444 | 0.444 | 0.333 |
| Neurology | 15 | 0.333 | 0.333 | 0.333 | 0.333 |
| Cardiology | 14 | 0.5 | 0.5 | 0.5 | 0.5 |
| Hematology and Immunology | 13 | 0.333 | 0.333 | 0.333 | 0.231 |
| Ophthalmology | 11 | 0.083 | 0.083 | 0.083 | 0.091 |
| Psychiatry and Sleep | 10 | 0.308 | 0.333 | 0.32 | 0.2 |
| Pediatrics and Development | 9 | 0.111 | 0.111 | 0.111 | 0.111 |

## Label quality

```
{
  "annotation_rows_by_status": {
    "ok": 2212,
    "not_final": 22,
    "unknown": 11
  },
  "not_in_release": [
    "M13.9"
  ],
  "category_not_final": [
    "G35",
    "I31.3",
    "I42.0",
    "I47.1",
    "M72.2",
    "R76.8"
  ],
  "visits_all_three_identical": 409,
  "visits": 510
}
```
