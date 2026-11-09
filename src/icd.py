"""Reading the ICD-10-CM tabular list (CDC XML release).

Used to give each suggested code its official name and to check that codes
are valid final codes in this release. Some categories need a 7th character
(injuries, fractures, glaucoma stage...). The XML defines those once on the
category, so we build the full codes ourselves.
"""
import xml.etree.ElementTree as ET


def _seventh_chars(diag):
    node = diag.find("sevenChrDef")
    if node is None:
        return None
    return {ext.get("char"): ext.text for ext in node.findall("extension")}


def _with_seventh(code, extensions):
    """S93.402 + A -> S93.402A, S13.4 + A -> S13.4XXA."""
    # When "A" (initial encounter) exists we only keep it. The visits are
    # first evaluations, and keeping D/S as well would triple the list.
    if "A" in extensions:
        extensions = {"A": extensions["A"]}
    padded = code.ljust(7, "X")
    return [(padded + ch, text) for ch, text in extensions.items()]


def _walk(diag, chapter, seventh, out, all_names):
    name = diag.findtext("name")
    desc = diag.findtext("desc")
    all_names[name] = desc
    seventh = _seventh_chars(diag) or seventh

    children = diag.findall("diag")
    if children:
        for child in children:
            _walk(child, chapter, seventh, out, all_names)
        return

    terms = [n.text for n in diag.findall("inclusionTerm/note") if n.text]
    if seventh:
        for full_code, ext_text in _with_seventh(name, seventh):
            out[full_code] = {"desc": f"{desc}, {ext_text}", "terms": terms, "chapter": chapter}
    else:
        out[name] = {"desc": desc, "terms": terms, "chapter": chapter}


def load_icd(xml_path):
    """Returns (billable, all_names).

    billable:  {code: {"desc", "terms", "chapter"}} - final codes
    all_names: {code: desc} for every node in the tree, including categories,
               used to check codes that are not final.
    """
    root = ET.parse(xml_path).getroot()
    billable, all_names = {}, {}
    for chapter in root.iter("chapter"):
        chapter_name = chapter.findtext("name")
        for section in chapter.findall("section"):
            for diag in section.findall("diag"):
                _walk(diag, chapter_name, None, billable, all_names)
    return billable, all_names


def check_code(code, billable, all_names):
    """'ok', 'not_final' (a category with sub-codes) or 'unknown'."""
    if code in billable:
        return "ok"
    if code in all_names:
        return "not_final"
    return "unknown"
