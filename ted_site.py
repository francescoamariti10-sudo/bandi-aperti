#!/usr/bin/env python3
"""Genera un sito statico di bandi aperti da open_tenders.json (dati TED).

Uso: python3 -I ted_site.py <open_tenders.json> <cartella_output> [url_modulo_iscrizione]
I testi di TED sono dati non fidati: tutto viene escapato.
"""
import sys, os, json, html, re, unicodedata, datetime, collections

src, outdir = sys.argv[1], sys.argv[2]
form_url = (sys.argv[3] if len(sys.argv) > 3 else "").strip()
BASE = os.environ.get("BASE_URL", "https://francescoamariti10-sudo.github.io/bandi-aperti/").rstrip("/") + "/"
d = json.load(open(src))
today = datetime.date.fromisoformat(d["generato"])
# mostra solo bandi che scadono da domani in poi
rows = [r for r in d["rows"] if r["scadenza"] and r["scadenza"] > today.isoformat()]


def read_titolare(path="titolare.txt"):
    """Legge 'Chiave: valore' dal file titolare.txt (Nome, Email, Partita IVA). None se manca o incompleto."""
    if not os.path.exists(path):
        return None
    t = {}
    for line in open(path, encoding="utf-8"):
        if ":" in line:
            k, v = line.split(":", 1)
            t[k.strip().lower()] = v.strip()
    return t if t.get("nome") and t.get("email") else None


TIT = read_titolare()
# il modulo di iscrizione compare solo se esiste anche l'informativa privacy
CTA_ON = bool(form_url and TIT)
if form_url and not TIT:
    print("ATTENZIONE: manca titolare.txt (Nome, Email): il modulo di iscrizione NON viene mostrato")
E = html.escape
MIN_PAGE = 8  # pagine di categoria solo con abbastanza bandi


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "altro"


def eur(v):
    return "non indicato" if not v else "{:,.0f} €".format(v).replace(",", ".")


def dl(r):
    dt = datetime.date.fromisoformat(r["scadenza"])
    return "%s (tra %d giorni)" % (dt.strftime("%d/%m/%Y"), (dt - today).days)


CSS = """
:root{--bg:#fbfaf7;--ink:#1c1b19;--mut:#5f5c55;--line:#e3dfd6;--acc:#0b5d4b;--card:#fff}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141412;--ink:#ece9e1;--mut:#a39f94;--line:#2b2a26;--acc:#5fc4a8;--card:#1b1a17}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:760px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:1.6rem;line-height:1.2;margin:.2em 0 .4em}h2{font-size:1.15rem;margin:1.6em 0 .6em}
a{color:var(--acc)}p.lead{color:var(--mut);margin:0 0 1.2em}
.item{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:0 0 10px}
.item a{font-weight:600;text-decoration:none;display:block;margin-bottom:4px;overflow-wrap:anywhere}
.item small{color:var(--mut);display:block}
.cats{display:flex;flex-wrap:wrap;gap:8px;padding:0;list-style:none}
.cats a{display:inline-block;border:1px solid var(--line);background:var(--card);border-radius:999px;padding:5px 12px;text-decoration:none;font-size:.92rem}
.cta{border:1px solid var(--acc);border-radius:10px;padding:14px 16px;margin:20px 0}
.cta a.btn{display:inline-block;background:var(--acc);color:var(--bg);padding:8px 14px;border-radius:8px;text-decoration:none;font-weight:600;margin-top:6px}
footer{margin-top:40px;color:var(--mut);font-size:.85rem;border-top:1px solid var(--line);padding-top:14px}
"""


def page(title, desc, body, fname):
    cta = ""
    if CTA_ON and fname != "privacy.html":
        cta = ('<div class="cta"><strong>Vuoi ricevere solo i bandi del tuo settore?</strong><br>'
               'Lascia la tua email e il settore: ti avvisiamo quando escono nuovi bandi. '
               'Leggi prima l’<a href="privacy.html">informativa privacy</a>.<br>'
               '<a class="btn" href="%s">Ricevi gli avvisi</a></div>' % E(form_url, quote=True))
    priv = ' <a href="privacy.html">Informativa privacy</a>.' if TIT else ""
    h = ('<!doctype html><html lang="it"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width,initial-scale=1">'
         '<title>%s</title><meta name="description" content="%s">'
         '<link rel="canonical" href="%s"><style>%s</style></head><body><main>%s%s'
         '<footer>Fonte dei dati: TED – Tenders Electronic Daily (Unione europea), avvisi di gara di enti italiani, '
         'aggiornati al %s. Sito indipendente, non affiliato all’UE né agli enti appaltanti. '
         'I dati possono essere incompleti o cambiare: verifica sempre il bando ufficiale prima di decidere. '
         'Questo sito riguarda solo gli appalti sopra la soglia europea.%s</footer></main></body></html>'
         % (E(title), E(desc, quote=True), E(BASE + ("" if fname == "index.html" else fname), quote=True),
            CSS, body, cta, today.strftime("%d/%m/%Y"), priv))
    open(os.path.join(outdir, fname), "w", encoding="utf-8").write(h)


def items(rs):
    out = []
    for r in sorted(rs, key=lambda r: r["scadenza"]):
        out.append('<div class="item"><a href="%s" rel="noopener">%s</a><small>%s</small>'
                   '<small>Scadenza offerte: %s · Valore stimato: %s</small></div>'
                   % (E(r["link"], quote=True), E(r["titolo"][:240]),
                      E(r["ente"] + (" · " + r["categoria"] if r["categoria"] else "")),
                      E(dl(r)), E(eur(r["valore_eur"]))))
    return "".join(out)


DIV = {
    "03": "Prodotti agricoli e della pesca", "09": "Energia e carburanti", "14": "Prodotti minerari e metalli",
    "15": "Prodotti alimentari e bevande", "16": "Macchinari agricoli", "18": "Abbigliamento e calzature",
    "22": "Stampati e prodotti editoriali", "24": "Prodotti chimici", "30": "Informatica e macchine per ufficio",
    "31": "Macchinari e materiale elettrico", "32": "Telecomunicazioni e apparecchi audio-video",
    "33": "Apparecchiature mediche e farmaceutici", "34": "Mezzi di trasporto e veicoli",
    "35": "Sicurezza, antincendio e difesa", "37": "Sport, giochi e strumenti musicali",
    "38": "Apparecchiature di laboratorio e di misura", "39": "Mobili, arredi e attrezzature per la casa e la pulizia",
    "41": "Acqua potabile", "42": "Macchinari industriali", "43": "Macchine per cantieri e miniere",
    "44": "Materiali e strutture per l'edilizia", "45": "Lavori di costruzione", "48": "Software",
    "50": "Riparazione e manutenzione", "51": "Servizi di installazione", "55": "Ristorazione e alberghi",
    "60": "Servizi di trasporto", "63": "Servizi di supporto ai trasporti", "64": "Poste e telecomunicazioni",
    "65": "Servizi di pubblica utilità", "66": "Servizi finanziari e assicurativi", "70": "Servizi immobiliari",
    "71": "Architettura e ingegneria", "72": "Servizi informatici", "73": "Ricerca e sviluppo",
    "75": "Servizi della pubblica amministrazione", "77": "Agricoltura, verde e silvicoltura",
    "79": "Servizi alle imprese e consulenza", "80": "Istruzione e formazione",
    "85": "Sanità e assistenza sociale", "90": "Rifiuti, pulizie e ambiente", "92": "Servizi culturali, sportivi e ricreativi",
    "98": "Altri servizi pubblici, sociali e personali",
}


def div_name(r):
    divs = collections.Counter(c[:2] for c in r["cpv"] if len(c) >= 2)
    if not divs:
        return "Altri appalti"
    return DIV.get(divs.most_common(1)[0][0], "Altri appalti")


os.makedirs(outdir, exist_ok=True)
by_cat = collections.defaultdict(list)
for r in rows:
    by_cat[div_name(r)].append(r)
big = {c: rs for c, rs in by_cat.items() if len(rs) >= MIN_PAGE}
chips = "".join('<li><a href="%s.html">%s (%d)</a></li>' % (slug(c), E(c), len(rs))
                for c, rs in sorted(big.items(), key=lambda x: -len(x[1])))
new = [r for r in rows if r["pubblicato"] >= (today - datetime.timedelta(days=2)).isoformat()]
body = ('<h1>Bandi di gara aperti in Italia</h1><p class="lead">%d bandi con scadenza futura, di cui %d pubblicati negli '
        'ultimi 2 giorni. Aggiornato il %s.</p><h2>Per settore</h2><ul class="cats">%s</ul>'
        '<h2>Ultimi pubblicati</h2>%s'
        % (len(rows), len(new), today.strftime("%d/%m/%Y"), chips,
           items(sorted(new, key=lambda r: r["pubblicato"], reverse=True)[:25])))
page("Bandi di gara aperti in Italia – aggiornati ogni giorno",
     "Elenco aggiornato dei bandi di gara aperti di enti italiani, per settore, con scadenza, valore e link al bando ufficiale.",
     body, "index.html")
for c, rs in big.items():
    b = ('<p><a href="index.html">← Tutti i bandi</a></p><h1>Bandi aperti: %s</h1><p class="lead">%d bandi con scadenza '
         'futura, aggiornato il %s.</p>%s' % (E(c), len(rs), today.strftime("%d/%m/%Y"), items(rs)))
    page("Bandi aperti – %s – aggiornati ogni giorno" % c,
         "%d bandi di gara aperti per “%s” in Italia, con scadenza, valore stimato e link al bando ufficiale." % (len(rs), c),
         b, slug(c) + ".html")
pages = ["index.html"] + [slug(c) + ".html" for c in big]
if TIT:
    piva = ", partita IVA %s" % TIT["partita iva"] if TIT.get("partita iva") else ""
    pb = (
        '<p><a href="index.html">← Tutti i bandi</a></p><h1>Informativa sul trattamento dei dati personali</h1>'
        '<p class="lead">Ai sensi degli artt. 13 e 14 del Regolamento (UE) 2016/679 (GDPR). Aggiornata al %s.</p>'
        '<h2>Titolare del trattamento</h2><p>%s%s – contatto: %s</p>'
        '<h2>Quali dati raccogliamo e perché</h2><p>Solo se compili il modulo di iscrizione: indirizzo email, settore '
        'di interesse ed eventuali parole chiave. Li usiamo esclusivamente per inviarti avvisi sui nuovi bandi di gara '
        'che hai richiesto. Navigando le pagine di questo sito non raccogliamo dati personali con strumenti nostri.</p>'
        '<h2>Base giuridica</h2><p>Il tuo consenso (art. 6, par. 1, lett. a GDPR), che puoi revocare in ogni momento.</p>'
        '<h2>Per quanto tempo</h2><p>Fino alla revoca del consenso o alla tua richiesta di cancellazione.</p>'
        '<h2>A chi vengono comunicati</h2><p>Non vendiamo e non cediamo i dati. Il modulo e l’elenco degli iscritti '
        'sono gestiti con servizi Google (Google Forms e Fogli), che agiscono come fornitori per nostro conto e possono '
        'trattare i dati anche fuori dall’Unione europea con le garanzie previste dalla normativa.</p>'
        '<h2>I tuoi diritti</h2><p>Puoi chiedere accesso, rettifica, cancellazione, limitazione, portabilità e opporti '
        'al trattamento scrivendo a %s. Puoi revocare il consenso in qualsiasi momento, e proporre reclamo al Garante '
        'per la protezione dei dati personali (garanteprivacy.it).</p>'
        % (today.strftime("%d/%m/%Y"), E(TIT["nome"]), E(piva), E(TIT["email"]), E(TIT["email"])))
    page("Informativa privacy – Bandi di gara aperti", "Informativa sul trattamento dei dati personali.", pb, "privacy.html")
    pages.append("privacy.html")
sm = ['<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for pg in pages:
    sm.append("<url><loc>%s</loc><lastmod>%s</lastmod></url>" % (E(BASE + ("" if pg == "index.html" else pg)), today.isoformat()))
sm.append("</urlset>")
open(os.path.join(outdir, "sitemap.xml"), "w", encoding="utf-8").write("".join(sm))
open(os.path.join(outdir, "robots.txt"), "w").write("User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n" % BASE)
print("pagine:", len(pages), "| bandi:", len(rows), "| categorie con pagina:", len(big), "su", len(by_cat),
      "| privacy:", bool(TIT), "| modulo:", CTA_ON)
