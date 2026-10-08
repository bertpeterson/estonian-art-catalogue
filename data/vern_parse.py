# -*- coding: utf-8 -*-
"""How a Vernissage product name is read -- shared by the shop harvest (vernissage.py)
and the auction-results harvest (vernissage_auctions.py). The name is one
period-separated string: artist first, a segment opening on a four-digit year is the
date (a span, reprint or decade too: "1946-51", "1972/2013", "U. 1942-43", "1930-ndad
II pool", "1960 – 70ndad aastad"; a medium run on after it, "1996 Õli", is the medium),
the segment carrying "cm" is the measurement, and what sits between is title and medium.
A point between digits is a decimal, not a break: "45.5 x 71 cm".
"""
import re

# a side may carry a stray space after its decimal comma: "Lm 85, 1 x 71 cm" is 85,1
_SIDE=r'\d+(?:[.,]\s?\d+)*'
DIM=re.compile(rf'({_SIDE}\s*[×x]\s*{_SIDE}(?:\s*[×x]\s*{_SIDE})?)\s*(cm|mm)', re.I)
YEAR=re.compile(r'^(1[89]\d\d|20[0-2]\d)(?!\d)')
# what may follow the year and still be the date: a span, a reprint, a decade, a part of one
TAIL=re.compile(r'(?:[\s\-–/]*(?:\d{2,4}(?!\d)|(?:ndate|ndad|nda|aastad|a|ii|i|pool|keskpaik|lõpp|algus)\b))*', re.I)
CIRCA=re.compile(r'^(u|ca|umbes)$', re.I)                 # "U. 1942-43": umbes, about
DROP=re.compile(r'^(müüdud|sold|reserveeritud|reserved|a|aastad)$', re.I)
# The name is one period-separated string and the year is not always there, so the
# medium cannot be found by position alone — "Martin Urb. Hommikune köök. Õli. Lõuend."
# has no year at all. Mediums are a closed vocabulary, so they can be recognised, and
# everything between the artist and the first medium word is the title.
MEDIUM = re.compile(r'^(õli|oil|lõuend|louend|canvas|akrüül|acrylic|tempera|guašš|akvarell|'
    r'õlimaal|watercolou?r|paber|paper|papp|card|graafika|serigraafia|silkscreen|ofort|etching|'
    r'litograafia|lithograph|lito|ofset|offset|linoollõige|puulõige|kuivnõel|drypoint|monotüüpia|segatehnika|'
    r'mixed media|tušš|ink|süsi|charcoal|pastell|pastel|pliiats|pencil|skulptuur|sculpture|'
    r'pronks|bronze|marmor|marble|kips|plaster|keraamika|ceramic|portselan|klaas|glass|'
    r'foto|photo|pigmenttrükk|digitrükk|autoritehnika|kollaaž|collage|reljeef|emailmaal|'
    r'vask|copper|teras|steel|puit|wood|lm|plm|raamitud|framed)\b', re.I)

def year_of(s):
    """(year, label, what follows) for a segment that opens on the date, else None."""
    m=YEAR.match(s)
    if not m: return None
    end=TAIL.match(s, m.end()).end()
    rest=s[end:].strip()
    if rest and not MEDIUM.match(rest): return None          # "1941 suvi" is a title
    label=re.sub(r'\s*a$', '', re.sub(r'\s*([-–/])\s*', r'\1', re.sub(r'\s+', ' ', s[:end].strip())))
    return m.group(1), label, rest

def parse(name):
    n=re.sub(r'\s+',' ', name).strip()
    segs=[s.strip() for s in re.split(r'(?<!\d)\.|\.(?!\d)', n) if s.strip()]
    segs=[x for i,s in enumerate(segs) for x in ((lambda y: [y[1], y[2]] if i and y and y[2] else [s])(year_of(s)))]
    segs=[s for s in segs if not DROP.match(s)]
    if len(segs)<2: return None
    artist=segs[0]
    if not re.match(r'^[^\d]{3,45}$', artist): return None
    yi=next((i for i,s in enumerate(segs[1:], 1) if year_of(s)), None)
    di=next((i for i,s in enumerate(segs) if DIM.search(s)), None)
    mi=next((i for i,s in enumerate(segs[1:], 1) if MEDIUM.match(s)), None)
    year,yl,_=year_of(segs[yi]) if yi is not None else (None,None,None)
    ci=yi-1 if yi and yi > 1 and CIRCA.match(segs[yi-1]) else None
    if ci: yl="ca "+yl
    dm=DIM.search(segs[di]) if di is not None else None
    dims=re.sub(r'([.,])\s+(?=\d)', r'\1', dm.group(1).strip())+" "+dm.group(2).lower() if dm else ""
    # the title ends at whichever marker comes first: the year, the medium, or the size
    stops=[x for x in (ci, yi, mi, di) if x is not None and x > 0]
    end=min(stops) if stops else len(segs)
    title=". ".join(segs[1:end]).strip().strip('„“”"')
    # the medium is what sits between the title and the measurement
    tstart=mi if mi is not None and (yi is None or mi > yi) else (yi+1 if yi is not None else end)
    tech=". ".join(s for s in segs[tstart:di] if not year_of(s)).strip() if di is not None \
         else ". ".join(s for s in segs[tstart:] if not year_of(s)).strip()
    if not title: return None
    return artist, title, year, tech, dims, (yl if yl != year else None)

