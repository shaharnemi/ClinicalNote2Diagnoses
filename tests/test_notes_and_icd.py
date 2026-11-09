from src.data import majority_labels
from src.icd import check_code, load_icd
from src.notes import clean_line, split_problems

NOTE = """ביקור מרפאתי. בן 68.
בבדיקה: דופלקס חיובי לקריש בווריד עמוק ימין.
לדברי המטופל/ת, נפיחות חד צדדית וכאב בשוק אחרי חוסר ניידות.
בסקירת מצב בריאותי נוסף עלה כי קוצר נשימה מתקדם עם עישון רב שנים.
הנתונים הרלוונטיים לכך: CT מציג שינויים אמפיזמטוטיים.
נבדקו התרופות הקבועות ומסמכים רפואיים קודמים."""


def test_split_problems():
    problems = split_problems(NOTE, boilerplate={"נבדקו התרופות הקבועות ומסמכים רפואיים קודמים."})
    assert len(problems) == 2
    assert problems[0][0] == "דופלקס חיובי לקריש בווריד עמוק ימין."
    assert problems[1] == ["קוצר נשימה מתקדם עם עישון רב שנים.", "CT מציג שינויים אמפיזמטוטיים."]


def test_clean_line():
    assert clean_line("ממצא תומך: שולי עפעף מודלקים.") == "שולי עפעף מודלקים."
    assert clean_line("מגיע/ה לבדיקה עקב גרד בעיניים.") == "גרד בעיניים."


def test_majority_labels():
    ann = {"V1": {"DR_A": ["A", "B"], "DR_B": ["A"], "DR_C": ["A", "B", "C"]}}
    assert majority_labels(ann) == {"V1": {"A", "B"}}


def test_icd_seventh_character():
    billable, names = load_icd("data/icd10cm-tabular-2027.xml")
    assert "S13.4XXA" in billable  # padded with X
    assert "H40.1122" in billable  # glaucoma stage
    assert check_code("G35", billable, names) == "not_final"
    assert check_code("M13.9", billable, names) == "unknown"
