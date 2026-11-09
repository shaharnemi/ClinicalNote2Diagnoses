"""Splitting a Hebrew visit note into separate clinical problems.

The notes have a regular structure: a header line (visit type + age), a few
lines per problem, and general closing lines ("סוכם על תוכנית טיפול...").
A new problem is opened by phrases like "נושא נוסף שהועלה בביקור".
"""
import re
from collections import Counter

HEADER = re.compile(r"^(ביקור מרפאתי|הערכה דחופה במוקד|ביקור טלפוני)")

NEW_PROBLEM = (
    "נושא נוסף שהועלה בביקור",
    "בנוסף, נדונה בעיה נפרדת",
    "תלונה נוספת שנבדקה",
    "בסקירת מצב בריאותי נוסף עלה כי",
)

# Openers that carry no clinical meaning. Anything short before a colon is
# also removed ("בבדיקה:", "ממצא תומך:" ...).
LEAD_INS = (
    "בסקירת מצב בריאותי נוסף עלה כי",
    "בימים האחרונים דווח כי",
    "מתאר/ת כי",
    "לדברי המטופל/ת,",
    "מגיע/ה לבדיקה עקב",
    "בהפניה מתוארת תמונה של",
)
COLON_PREFIX = re.compile(r"^[^:]{2,45}:\s*")


def note_lines(note):
    return [line.strip() for line in note.splitlines() if line.strip()]


def find_boilerplate(notes, min_count=20):
    """Lines that repeat across many notes are general text, not findings."""
    counts = Counter(line for note in notes for line in set(note_lines(note)))
    return {line for line, n in counts.items() if n >= min_count}


def clean_line(line):
    for lead in LEAD_INS:
        if line.startswith(lead):
            return line[len(lead):].strip()
    return COLON_PREFIX.sub("", line).strip()


def split_problems(note, boilerplate=()):
    """Returns a list of problems, each a list of cleaned lines."""
    problems = []
    for line in note_lines(note):
        if HEADER.match(line) or line in boilerplate:
            continue
        if not problems or line.startswith(NEW_PROBLEM):
            problems.append([])
        cleaned = clean_line(line)
        if cleaned:
            problems[-1].append(cleaned)
    return [p for p in problems if p]
