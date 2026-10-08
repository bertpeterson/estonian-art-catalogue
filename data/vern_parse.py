# -*- coding: utf-8 -*-
"""How a Vernissage product name is read -- shared by the shop harvest (vernissage.py)
and the auction-results harvest (vernissage_auctions.py). The name is one
period-separated string: artist first, a four-digit segment is the year (or a span or
reprint: "1946-51", "1972/2013", "U. 1942-43"), the segment carrying "cm" is the
measurement, and what sits between is title and medium.
"""
import re

DIM=re.compile(r'([\d.,]+\s*[×x]\s*[\d.,]+(?:\s*[×x]\s*[\d.,]+)?)\s*(cm|mm)', re.I)
YEAR=re.compile(r'^(1[89]\d\d|20[0-2]\d)(\s*[-–/]\s*(?:1[89]\d\d|20[0-2]\d|\d{2}))?\.?\s*(?:a\.?)?$')
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

def parse(name):
    n=re.sub(r'\s+',' ', name).strip()
    segs=[s.strip() for s in n.split('.') if s.strip()]
    segs=[s for s in segs if not DROP.match(s)]
    if len(segs)<2: return None
    artist=segs[0]
    if not re.match(r'^[^\d]{3,45}$', artist): return None
    yi=next((i for i,s in enumerate(segs) if YEAR.match(s)), None)
    di=next((i for i,s in enumerate(segs) if DIM.search(s)), None)
    mi=next((i for i,s in enumerate(segs[1:], 1) if MEDIUM.match(s)), None)
    year=re.match(r'^(\d{4})', segs[yi]).group(1) if yi is not None else None
    yl=re.sub(r'\s+', '', YEAR.match(segs[yi]).group(0)).rstrip('.') if yi is not None else None
    ci=yi-1 if yi and yi > 1 and CIRCA.match(segs[yi-1]) else None
    if ci: yl="ca "+yl
    dm=DIM.search(segs[di]) if di is not None else None
    dims=f"{dm.group(1).strip()} {dm.group(2).lower()}" if dm else ""
    # the title ends at whichever marker comes first: the year, the medium, or the size
    stops=[x for x in (ci, yi, mi, di) if x is not None and x > 0]
    end=min(stops) if stops else len(segs)
    title=". ".join(segs[1:end]).strip().strip('„“”"')
    # the medium is what sits between the title and the measurement
    tstart=mi if mi is not None and (yi is None or mi > yi) else (yi+1 if yi is not None else end)
    tech=". ".join(s for s in segs[tstart:di] if not YEAR.match(s)).strip() if di is not None \
         else ". ".join(s for s in segs[tstart:] if not YEAR.match(s)).strip()
    if not title: return None
    return artist, title, year, tech, dims, (yl if yl != year else None)

