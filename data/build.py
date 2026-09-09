# -*- coding: utf-8 -*-
import json, re, collections, unicodedata, datetime

ESS = {"maal":"Painting","graafika":"Print","skulptuur":"Sculpture","joonistus":"Drawing",
 "installatsioon":"Installation","videosalvestis":"Video","reljeef":"Relief","kollaaž":"Collage",
 "foto":"Photograph","akvarell":"Watercolour","film":"Film","digitaalne kujutis":"Digital image",
 "plastika":"Sculpture","illustratsioon":"Illustration","segatehnika":"Mixed media","objekt":"Object",
 "keraamika":"Ceramics","medal":"Medal","pastell":"Pastel","tempera":"Tempera","monotüüpia":"Monotype",
 "eksliibris":"Bookplate","gvašš":"Gouache","guašš":"Gouache","vaip":"Tapestry","mosaiik":"Mosaic",
 "vitraaž":"Stained glass","assamblaaž":"Assemblage","emailmaal":"Enamel"}

TECH = {"õli":"oil","ofort":"etching","tušš":"ink","valamine":"casting","guašš":"gouache",
 "gvašš":"gouache","pastell":"pastel","linoollõige":"linocut","litograafia":"lithography",
 "akvarell":"watercolour","raiumine":"carving","pliiats":"pencil","tempera":"tempera",
 "puulõige":"woodcut","akrüül":"acrylic","segatehnika":"mixed technique",
 "autoritehnika":"artist's own technique","vasegravüür":"copper engraving","kuivnõel":"drypoint",
 "akvatint":"aquatint","akvatinta":"aquatint","süsi":"charcoal","söejoonistus":"charcoal",
 "serigraafia":"screenprint","siiditrükk":"screenprint","mezzotinto":"mezzotint","mezzotinta":"mezzotint",
 "kollaaž":"collage","monotüüpia":"monotype","digitaaltrükk":"digital print","fotograafia":"photography",
 "video":"video","modelleerimine":"modelling","tikkimine":"embroidery","email":"enamel",
 "keraamika":"ceramic","klaas":"glass","sulejoonistus":"pen drawing","kriit":"chalk",
 "sangviin":"sanguine","vahatehnika":"encaustic","voolimine":"modelling","tahvelmaal":"panel painting",
 "gravüür":"engraving","ofortimine":"etching","söövitus":"etching","trükkimine":"printing",
 "maalimine":"painting","joonistamine":"drawing","freskomaal":"fresco","seinamaal":"mural",
 "valu":"cast","treimine":"turning","tempermaal":"tempera","kuivnõeltehnika":"drypoint",
 "lavis":"wash","laveering":"wash","pintsel":"brush","sulg":"pen","viltpliiats":"felt-tip",
 "aerograafia":"airbrush","fotomontaaž":"photomontage","assamblaaž":"assemblage"}

MAT = {"lõuend":"canvas","lõuend (riidesort)":"canvas","paber":"paper","papp":"board","vineer":"plywood",
 "pronks":"bronze","kips":"plaster","kips (valge)":"plaster","kartong":"card","puit":"wood",
 "puitkiudplaat":"fibreboard","marmor":"marble","marmor (valge)":"marble","tekstiil":"textile",
 "keraamika":"ceramic","šamott":"chamotte","masoniit":"masonite","pleksiklaas":"perspex",
 "metall":"metal","graniit":"granite","dolomiit":"dolomite","savi":"clay","kivi":"stone",
 "tsement":"cement","alumiinium":"aluminium","teras":"steel","klaas":"glass","siid":"silk",
 "nahk":"leather","plastik":"plastic","betoon":"concrete","raud":"iron","vask":"copper",
 "hõbe":"silver","kuld":"gold","kartongpapp":"card","lubjakivi":"limestone","kunstkivi":"artificial stone",
 "sünteetiline材":"synthetic","tempera":"tempera","õlivärv":"oil paint","akrüülvärv":"acrylic paint"}

# birth/death years for living or MuIS-silent artists — editorial, not from MuIS
ED_LIFE = {
"Aili Vint":["1941",""],"Alexei Gordin":["1989",""],"Andres Tolts":["1949","2014"],
"August Künnapu":["1974",""],"Dénes Farkas":["1974",""],"Edith Karlson":["1983",""],
"Ene-Liis Semper":["1969",""],"Evi Tihemets":["1932","2022"],"Flo Kasearu":["1985",""],
"Herald Eelma":["1934","2010"],"Jaak Soans":["1943",""],"Jaan Elken":["1954",""],
"Jaan Toomik":["1961",""],"Jaanus Samma":["1982",""],"Jass Kaselaan":["1975",""],
"Jüri Ojaver":["1955",""],"Kaarel Kurismaa":["1939",""],"Kaido Ole":["1963",""],
"Karel Koplimets":["1986",""],"Katja Novitskova":["1984",""],"Kiwa":["1975",""],
"Kris Lemsalu":["1985",""],"Krista Mölder":["1972",""],"Mall Nukke":["1964",""],
"Marge Monko":["1976",""],"Mari Kurismaa":["1956",""],"Mark Raidpere":["1975",""],
"Marko Mäetamm":["1965",""],"Mati Karmin":["1959",""],"Merike Estna":["1980",""],
"Navitrolla":["1970",""],"Olav Maran":["1933",""],"Paul Kuimet":["1984",""],
"Peeter Laurits":["1962",""],"Raoul Kurvitz":["1961",""],"Raul Meel":["1941",""],
"Raul Rajangu":["1963",""],"Rein Tammik":["1947",""],"Sigrid Viir":["1979",""],
"Siim-Tanel Annus":["1960",""],"Sirje Runge":["1950",""],"Tanja Muravskaja":["1978",""],
"Tiit Pääsuke":["1941",""],"Timo Toots":["1982",""],"Toomas Vint":["1944",""],
"Vello Vinn":["1939",""]}

ED_BIO = {
"Ado Vabbe":"Brought Kandinsky's line to Tartu; long-serving professor at the Pallas school.",
"Aili Vint":"Painter of luminous, near-abstract sea and horizon studies.",
"Aleksander Vardi":"Pallas-trained colourist of Tartu landscapes and still lifes.",
"Alexei Gordin":"Painter and video artist of the precarious artist's life, in deadpan Russian-Estonian.",
"Amandus Adamson":"Sculptor of the Russalka memorial; trained in St Petersburg, worked in Paris and Paldiski.",
"Ando Keskküla":"Hyperrealist, later video artist and rector of the Estonian Academy of Arts.",
"Andres Tolts":"Pop and hyperrealist painter and designer, member of SOUP'69.",
"Andrus Johani":"Pallas painter of Tartu streets and interiors; killed in 1941, aged 34.",
"Ants Laikmaa":"Pastel portraitist and teacher; founded an influential private studio school in Tallinn.",
"August Künnapu":"Painter of flat, affectionate portraits of public figures and buildings.",
"Concordia Klar":"Printmaker of severe geometric compositions.",
"Dénes Farkas":"Photographer and book artist working between language and translation.",
"Edith Karlson":"Sculptor of concrete and clay animals staging human moral scenes.",
"Eduard Ole":"Pallas-trained painter; emigrated to Sweden in 1944.",
"Eerik Haamer":"Painter of coastal and island people; fled to Sweden in 1944.",
"Ene-Liis Semper":"Video artist and theatre director; co-founder of Theatre NO99.",
"Eugen Dücker":"Baltic-German landscape painter; professor at the Düsseldorf Academy.",
"Gerhard von Kügelgen":"MuIS dates this Gerhard von Kügelgen 1806–1883 — a later member of the Baltic-German Kügelgen family of painters, not the Romantic portraitist (1772–1820) of the same name.",
"Henrik Olvi":"Graphic artist and painter of the interwar Tartu circle.",
"Jaan Toomik":"Video artist and painter; Estonia's most internationally shown artist of the 1990s.",
"Jass Kaselaan":"Sculptor of heavy, memorial-scale objects with a horror undertow.",
"Juhan Muks":"Pallas painter of stark, simplified figures and landscapes.",
"Julie Hagen-Schwarz":"The first professionally trained woman artist in Estonia; portraitist, trained in Dresden and Italy.",
"Jüri Palm":"Painter and graphic artist of the 1960s Tartu generation.",
"Kaarel Liimand":"Pallas painter of rural labour; died in 1941.",
"Kaido Ole":"Painter of constructed, deadpan figures and pictorial systems.",
"Kaja Kärner":"Tartu painter who worked toward abstraction outside official exhibition life.",
"Kaljo Põllu":"Led ANK'64; later turned to Finno-Ugric prehistory in mezzotint.",
"Karel Koplimets":"Artist of investigations and reconstructions, working in photography, video and installation.",
"Karin Luts":"Painter of interior and female subjects; emigrated to Sweden in 1944.",
"Katja Novitskova":"Post-internet artist working with image ecology, biotech and the digital creature.",
"Kiwa":"Conceptual artist, poet and publisher on the post-Soviet margin.",
"Kris Lemsalu":"Ceramic and performance artist of hybrid, half-animal bodies.",
"Krista Mölder":"Photographer of thresholds, empty rooms and the edge of the visible.",
"Kristjan Raud":"National romantic draughtsman; his charcoal Kalevipoeg cycle defined how Estonians picture their epic.",
"Kuno Veeber":"Cubist-influenced Pallas painter; died at 31.",
"Lola Liivat":"Abstract painter; worked in Tartu from the 1950s to her nineties.",
"Mall Nukke":"Collagist and painter reworking Soviet and religious imagery.",
"Malle Leis":"Silkscreen and watercolour flowers with pop clarity.",
"Marge Monko":"Photographer and video artist on labour, desire and the display window.",
"Mari Kurismaa":"Painter of architectural interiors emptied of people.",
"Mark Raidpere":"Photographer and video artist of the intimate portrait.",
"Marko Mäetamm":"Painter, printmaker and video artist working the black comedy of family life.",
"Mati Karmin":"Sculptor; known both for public monuments and for furniture made from naval mines.",
"Merike Estna":"Painter who extends the painting onto floors, clothes and bodies.",
"Navitrolla":"Naive painter of wide, animal-populated landscapes; the most reproduced living Estonian artist.",
"Olav Maran":"Founder member of ANK'64; surrealist, then a painter of quiet still lifes.",
"Paul Kuimet":"Photographer and film artist working on architecture, material and light.",
"Peeter Laurits":"Photographer and early digital montagist; ecology as image manipulation.",
"Raoul Kurvitz":"Founder of Group T; installation, performance and painting after the collapse.",
"Raul Meel":"Concrete poet and printmaker; systematic, serial, obsessive.",
"Raul Rajangu":"Painter of the late-Soviet transavantgarde.",
"Rein Tammik":"Hyperrealist painter of the 1970s generation.",
"Sigrid Viir":"Photographer and installation artist on work, routine and the staged everyday.",
"Siim-Tanel Annus":"Performance artist of fire rituals staged in his father's Tallinn garden.",
"Sirje Runge":"Geometric abstractionist; her 1970s urban design projects were decades early.",
"Tanja Muravskaja":"Photographer on nationality, belonging and the politics of the portrait.",
"Tiit Pääsuke":"Painter of the 1970s generation; figure and still life under hard light.",
"Timo Toots":"Media artist working with data, surveillance and the machinery of e-Estonia.",
"Toomas Vint":"Painter and novelist; landscapes with something quietly wrong in them.",
"Vello Vinn":"Graphic artist of intricate, machine-like fantasy worlds.",
"Anna-Stina Treumund":"Photographer and activist who made Estonian queer and feminist life visible.",
"Flo Kasearu":"Artist of institutions and property; her own house is her museum.",
"Jaanus Samma":"Artist-archivist of queer histories suppressed in Soviet Estonia.",
"Jaan Elken":"Painter moving between abstract expressionism and urban text-surfaces.",
"Jaak Soans":"Sculptor of public monuments and restrained portrait heads.",
"Jüri Ojaver":"Sculptor and installation artist of the transition years.",
"Kaarel Kurismaa":"Pioneer of kinetic and sound art in Estonia.",
"Herald Eelma":"Graphic artist and book illustrator of the post-war generation.",
"Evi Tihemets":"Printmaker whose etchings moved from figuration to lyrical abstraction.",
"Peeter Allik":"Graphic artist and painter of savage, grotesque satire, working in Tartu.",
"Oskar Hoffmann":"Painter of Estonian peasant genre scenes; trained in Düsseldorf and Munich.",
"Valve Janov":"Tartu abstractionist who worked outside official exhibition life for decades.",
"Silvia Jõgever":"Tartu painter of restrained, tonal figure and landscape compositions.",
"Nikolai Kormašov":"Painter and icon collector; a bridge between Russian and Estonian art in Tallinn.",
"Villem Ormisson":"Pallas painter of southern light and Estonian landscape; died in 1941.",
"Paul Raud":"Portraitist of Muhu and Saaremaa islanders; twin brother of Kristjan Raud.",
"Richard Sagrits":"Landscape painter and muralist of the Pallas generation.",
"Peeter Ulas":"Graphic artist of dense, visionary etchings and mezzotints.",
"Tõnis Vint":"Geometric abstractionist and teacher; a school of one in Soviet Tallinn.",
"Ülo Õun":"Sculptor of unsparing, psychologically exposed figures.",
"Aleksander Uurits":"Symbolist painter and draughtsman of the Noor-Eesti generation; died at 30.",
}

def esc_ess(e):
    first = re.split(r'[;/]', e or "")[0].strip().lower()
    return ESS.get(first, first.capitalize() if first else "Other"), first

def term(v, table):
    if not v: return None, None
    parts = [p.strip() for p in re.split(r'[;,]', v) if p.strip()]
    en = [table.get(p.lower(), p) for p in parts[:3]]
    return "; ".join(en), v

def year_of(d):
    if not d: return None, None
    s = d.strip()
    ys = [int(x) for x in re.findall(r'\b(1[5-9]\d\d|20[0-4]\d)\b', s)]
    if not ys:
        m = re.search(r'\b(1[5-9]|20)(\d)0?\s*ndat?e?\b', s)
        return None, s
    y = ys[0]
    lab = s.replace("on oletatav ", "c. ").replace(" - ", "–")
    return y, lab

R = json.load(open("records.json", encoding="utf-8"))
by_artist = collections.defaultdict(list)
for r in R: by_artist[r["artist"]].append(r)

artists, aidx = [], {}
for name in sorted(by_artist, key=lambda n: (n.split()[-1], n)):
    recs = by_artist[name]
    life = next((r["life"] for r in recs if r.get("life")), None)
    lsrc = "muis"
    if not life:
        life = ED_LIFE.get(name); lsrc = "ed"
    bios = [r["bio"] for r in recs if r.get("bio")]
    bio = max(bios, key=len) if bios else None
    bsrc = "muis"
    if not bio:
        bio = ED_BIO.get(name); bsrc = "ed"
    aidx[name] = len(artists)
    artists.append({"n": name, "l": life or ["", ""], "ls": lsrc,
                    "b": (bio or "")[:1200], "bs": bsrc if bio else None})

works = []
for r in R:
    y, lab = year_of(r.get("date"))
    en_e, et_e = esc_ess(r.get("essence"))
    tc, tce = term(r.get("tech"), TECH)
    mt, mte = term(r.get("mat"), MAT)
    works.append({
      "a": aidx[r["artist"]], "t": r["title"].strip(),
      "y": y, "yl": lab,
      "e": en_e, "ee": et_e,
      "tc": tc, "tce": tce, "m": mt, "me": mte,
      "dm": r.get("dims") or None,
      "mu": r.get("museum"), "co": r.get("collection"),
      "nu": r.get("num"), "d": (r.get("desc") or None), "id": r["id"]})

for a in artists:
    a["c"] = sum(1 for w in works if w["a"] == aidx[a["n"]])

data = {"meta": {"built": datetime.date.today().isoformat(),
                 "source": "Muuseumide Infosüsteem (MuIS), Estonian Ministry of Culture — metadata CC0",
                 "works": len(works), "artists": len(artists),
                 "dated": sum(1 for w in works if w["y"]),
                 "museums": sorted({w["mu"] for w in works if w["mu"]})},
        "artists": artists, "works": works}
json.dump(data, open("data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
import os
print("data.json", os.path.getsize("data.json")//1024, "KB")
print("works", len(works), "artists", len(artists), "dated", data["meta"]["dated"])
dec = collections.Counter((w["y"]//10*10) for w in works if w["y"])
print("decades:", " ".join(f"{k}s:{v}" for k, v in sorted(dec.items())))
print("life src:", collections.Counter(a["ls"] for a in artists))
print("bio src:", collections.Counter(a["bs"] for a in artists))
