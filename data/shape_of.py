# -*- coding: utf-8 -*-
"""height over width from a record's dimensions string -- shared by build_site.py and chart_side.py"""
import re

def shape_of(dm):
    """height over width from a dimensions string: '41.0 x 26.0 cm', or the labelled
    'lehe kõrgus: 28.0 cm; lehe laius: 34.9 cm' MuIS writes for sheets"""
    dm = str(dm or "")
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)", dm)
    if m: a, b = m.group(1), m.group(2)
    else:
        # MuIS labels each measure -- "lehe kõrgus", "graafikaplaadi laius", "kõrgus (raamiga)"
        # -- and a print carries the sheet's and the plate's; pair like with like, the
        # sheet first (it is what the photograph shows), never a plate height with a
        # sheet width
        pairs = {}
        for q, kind, v in re.findall(r"(?:^|;)\s*([^;:]*?)(kõrgus|laius)\s*:\s*(\d+(?:[.,]\d+)?)", dm):
            pairs.setdefault(q.strip(), {})[kind] = v
        pick = next((pairs[q] for q in ("lehe ", "lehe", "", "graafikaplaadi ", "kujutise ") if q in pairs and len(pairs[q]) == 2), None)
        if not pick: pick = next((v for v in pairs.values() if len(v) == 2), None)
        if not pick: return None
        a, b = pick["kõrgus"], pick["laius"]
    b = float(b.replace(",", "."))
    return float(a.replace(",", ".")) / b if b else None
