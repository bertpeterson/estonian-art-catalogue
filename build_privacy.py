# -*- coding: utf-8 -*-
"""The privacy page: /privacy.html and /privaatsus.html.

What museaal keeps about a visitor and who else sees what, in plain words. Every claim is one worker/template.js or
list-sync.js makes true: the KV keys and their lifetimes (t: 15 minutes, s: a year, u: two years from the list's last
change, n: until stopped or the account deleted), Resend for the emails, Turnstile before an email or a Claude call,
the messages to Claude not kept. Change the page when the Worker changes. Linked from the sign-in panel, the account
page, the footers (CONTACT in build_hubs.py and build_pages.py, "foot" in i18n.py) and so Buy Art's "Sources &
privacy". In the sitemap. Run before csp.py, which hashes the theme stamp.
"""
import datetime, html
from build_account import CSS, STAMP, GC

e = lambda s: html.escape(str(s or ""), quote=True)
BASE = "https://museaal.ee"
MAIL = '<a href="mailto:info@museaal.ee">info@museaal.ee</a>'

T = {
    "en": dict(file="privacy", other="privaatsus", other_l="Eesti keeles", site="Estonian Art Catalogue", home="./",
               title="Privacy", back="Back to the catalogue",
               lede="What museaal.ee keeps about you, and who else sees what. Updated 15 October 2026.",
               parts=[
        ("Who runs it", [f"museaal.ee is an independent catalogue, run privately: not by a museum, a gallery or an auction house. "
                         f"Questions, corrections and requests about your data: {MAIL}."]),
        ("Browsing", ["You can use the whole catalogue without an account. museaal sets no cookies. My List and the light or dark "
                      "setting are kept in your browser's own storage, on your device, until you clear it.",
                      "Visits are counted with GoatCounter, without cookies and without personal data: which page was seen, not by whom. "
                      "A sign-in link sent and a sign-in are counted the same way.",
                      "Museum pictures are shown straight from MuIS and the Art Museum of Estonia, gallery pictures from the gallery's own "
                      "server, and the fonts come from Google Fonts: those servers see your browser's request, as with any web page. "
                      "The site itself is served by GitHub Pages."]),
        ("Accounts", ["An account is only for having My List on all your devices. We keep your email address and your list in Cloudflare's "
                      "storage (Workers KV) until you delete the account, or until the list has gone unchanged for two years. "
                      "The address is used only to send you sign-in links, and the news emails below if you ask for them.",
                      "A sign-in link works once, for 15 minutes; a sign-in lasts a year on that device, or until you sign out. "
                      "Accounts made before 15 October 2026 kept no address; theirs is kept from the next sign-in."]),
        ("News emails", ["Only if you ask: tick the box when you sign in and open the link we send, or turn them on from your account page. "
                         "Every one carries an unsubscribe link, and you can stop them any time, there or on your account page. "
                         "Until you stop them or delete your account we keep your address, your language and when you said yes."]),
        ("The Buy Art assistant and art by mood", ["What you type to the Buy Art assistant, with the works on My List, and the words you type on "
                         "the mood page are sent to Claude, Anthropic's AI model, to answer. museaal does not keep them; "
                         "it counts only how many there were each day."]),
        ("Who handles it for us", ["Cloudflare runs the part that answers (a Worker), holds the accounts (Workers KV) and checks "
                         "that you are not a robot (Turnstile) before an email is sent or the assistant answers. "
                         "Resend sends the emails, from its EU region. Anthropic answers the assistant and the mood page. "
                         "GoatCounter counts the visits."]),
        ("Your rights", ["You can see, correct or delete your data. Your account page shows your address; Delete account there removes "
                         f"the address, our copy of the list and the news emails at once. Or write to {MAIL}. "
                         "If you think we handle your data wrongly, you can complain to the Estonian Data Protection Inspectorate "
                         '(Andmekaitse Inspektsioon, <a href="https://www.aki.ee/en">aki.ee</a>).']),
    ]),
    "et": dict(file="privaatsus", other="privacy", other_l="In English", site="Eesti Kunstikataloog", home="./#lang=et",
               title="Privaatsus", back="Tagasi kataloogi",
               lede="Mida museaal.ee sinu kohta hoiab ja kes mida näeb. Uuendatud 15. oktoobril 2026.",
               parts=[
        ("Kes seda peab", [f"museaal.ee on sõltumatu, eraviisiliselt peetav kataloog: mitte muuseumi, galerii ega oksjonimaja oma. "
                           f"Küsimused, parandused ja soovid sinu andmete kohta: {MAIL}."]),
        ("Sirvimine", ["Kogu kataloogi saab kasutada ilma kontota. museaal ei sea küpsiseid. Minu nimekiri ning hele või tume vaade "
                       "on sinu brauseri enda mälus, sinu seadmes, kuni selle tühjendad.",
                       "Külastusi loeb GoatCounter, ilma küpsiste ja isikuandmeteta: milline leht vaadati, mitte kes vaatas. "
                       "Saadetud sisselogimislinke ja sisselogimisi loetakse samamoodi.",
                       "Muuseumide pildid tulevad otse MuISist ja Eesti Kunstimuuseumist, galeriide pildid galerii enda serverist ning "
                       "kirjatüübid Google Fontsist: need serverid näevad sinu brauseri päringut nagu iga veebilehe puhul. "
                       "Lehte ennast serveerib GitHub Pages."]),
        ("Kontod", ["Konto on ainult selleks, et Minu nimekiri oleks kõigis sinu seadmetes. Sinu e-posti aadressi ja nimekirja hoiame "
                    "Cloudflare'i andmehoidlas (Workers KV), kuni kustutad konto või kuni nimekiri on kaks aastat muutmata. "
                    "Aadressi kasutame ainult sisselogimislinkide saatmiseks ja allpool kirjeldatud uudiskirjadeks, kui neid soovid.",
                    "Sisselogimislink töötab üks kord ja 15 minutit; sisselogimine kehtib selles seadmes aasta või kuni välja logid. "
                    "Enne 15. oktoobrit 2026 loodud kontod aadressi ei hoidnud; nende aadressi hoitakse alates järgmisest sisselogimisest."]),
        ("Uudiskirjad", ["Ainult siis, kui soovid: tee sisselogimisel linnuke ja ava saadetud link või lülita need sisse oma konto lehel. "
                         "Igas kirjas on loobumislink ja saad need igal ajal lõpetada, seal või oma konto lehel. "
                         "Kuni lõpetad või konto kustutad, hoiame sinu aadressi, keelt ja aega, millal nõustusid."]),
        ("Kunstiostu abiline ja kunst meeleolu järgi", ["See, mida kirjutad kunstiostu abilisele, koos Minu nimekirja teostega, ja sõnad, "
                         "mida kirjutad meeleolu lehel, saadetakse vastamiseks Anthropicu tehisintellekti mudelile Claude. "
                         "museaal neid ei hoia; loeme ainult, mitu neid päevas oli."]),
        ("Kes neid meie eest käsitleb", ["Cloudflare käitab vastavat osa (Worker), hoiab kontosid (Workers KV) ja kontrollib "
                         "(Turnstile), et sa pole robot, enne kui kiri saadetakse või abiline vastab. "
                         "Resend saadab e-kirjad oma ELi piirkonnast. Anthropic vastab abilisele ja meeleolu lehele. "
                         "GoatCounter loeb külastusi."]),
        ("Sinu õigused", ["Saad oma andmeid näha, parandada või kustutada. Konto lehel on näha sinu aadress; seal „Kustuta konto” "
                          f"eemaldab korraga aadressi, meie koopia nimekirjast ja uudiskirjad. Või kirjuta {MAIL}. "
                          "Kui leiad, et käsitleme sinu andmeid valesti, võid pöörduda Andmekaitse Inspektsiooni poole "
                          '(<a href="https://www.aki.ee">aki.ee</a>).']),
    ]),
}

MORE = ("main section{padding:22px 0;border-bottom:1px solid var(--rule-soft)}main section:last-child{border-bottom:0}"
        "main p{margin:0 0 10px;max-width:64ch;color:var(--ink-soft)}main p:last-child{margin-bottom:0}"
        "main a{text-decoration-color:var(--grey)}main a:hover{text-decoration-color:var(--ink)}")

def page(lang):
    p = T[lang]
    body = "".join(f'<section><h2>{e(h)}</h2>' + "".join(f"<p>{x}</p>" for x in ps) + "</section>" for h, ps in p["parts"])
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">{STAMP}<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(p["title"])} · museaal.ee</title><meta name="description" content="{e(p["lede"])}">'
            f'<link rel="canonical" href="{BASE}/{p["file"]}">'
            f'<link rel="alternate" hreflang="{lang}" href="{BASE}/{p["file"]}"><link rel="alternate" hreflang="{"et" if lang == "en" else "en"}" href="{BASE}/{p["other"]}">'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400..600;1,6..72,400..600&family=Archivo:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">'
            f'<style>{CSS}{MORE}</style>{GC}</head><body><div class="pg">'
            f'<div class="top"><a class="wm" href="{p["home"]}">{e(p["site"])}</a><a class="eb" href="{p["other"]}" hreflang="{"et" if lang == "en" else "en"}">{p["other_l"]}</a></div>'
            f'<header class="mast"><h1>{e(p["title"])}</h1><p class="lede">{e(p["lede"])}</p></header><main>{body}</main>'
            f'<footer class="foot"><a href="{p["home"]}">{e(p["back"])}</a> · {MAIL}</footer></div></body></html>')

def main():
    urls = []
    for lang in ("en", "et"):
        open(f"site/{T[lang]['file']}.html", "w", encoding="utf-8").write(page(lang)); urls.append(f"{BASE}/{T[lang]['file']}")
    sm = open("site/sitemap.xml", encoding="utf-8").read()
    today = datetime.date.today().isoformat()
    add = "".join(f'<url><loc>{u}</loc><lastmod>{today}</lastmod><changefreq>yearly</changefreq></url>' for u in urls)
    open("site/sitemap.xml", "w", encoding="utf-8").write(sm.replace("</urlset>", add + "</urlset>"))
    print("  privacy page   privacy.html, privaatsus.html")

if __name__ == "__main__":
    main()
