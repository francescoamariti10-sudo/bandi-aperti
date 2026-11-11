#!/usr/bin/env python3
"""Scarica da TED (API anonima v3) i bandi aperti di enti italiani e li salva in JSON.

Uso: python3 -I ted_fetch.py <giorni_indietro> <file_output>
Solo libreria standard. I testi che arrivano da TED sono dati non fidati: qui vengono
solo letti e salvati, mai eseguiti.
"""
import sys, json, time, datetime, html, re, urllib.request, urllib.error

API = "https://api.ted.europa.eu/v3/notices/search"
FIELDS = [
    "publication-number", "publication-date", "notice-title", "buyer-name",
    "notice-type", "classification-cpv", "deadline-receipt-tender-date-lot",
    "estimated-value-lot", "estimated-value-cur-lot",
]
OPEN_TYPES = ("cn-standard", "cn-social", "cn-desg", "cn-standard-v2")  # avvisi di gara (bando)


def post(body, retries=3):
    data = json.dumps(body).encode()
    for i in range(retries):
        try:
            req = urllib.request.Request(API, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read()[:300]
            if e.code in (429, 503) and i < retries - 1:
                time.sleep(5 * (i + 1))
                continue
            raise SystemExit("HTTP %s: %s" % (e.code, msg))
        except Exception as e:  # rete
            if i < retries - 1:
                time.sleep(3)
                continue
            raise SystemExit("errore rete: %s" % e)


def pick_title(t):
    """Ritorna (categoria, titolo) preferendo l'italiano."""
    if not isinstance(t, dict) or not t:
        return "", ""
    s = t.get("ita") or next(iter(t.values()))
    if isinstance(s, list):
        s = s[0] if s else ""
    s = html.unescape(s)
    parts = s.split(" – ", 2)
    cat, title = ("", s.strip())
    if len(parts) == 3:
        cat, title = parts[1].strip(), parts[2].strip()
    # titoli che sono solo un numero di riferimento (es. "118/2026"): usa la categoria
    if cat and (len(title) < 12 or re.fullmatch(r"[\d/\-\s.]+", title)):
        title = "%s (rif. %s)" % (cat, title)
    return cat, title


def first(v):
    if isinstance(v, dict):
        v = v.get("ita") or next(iter(v.values()), [])
    if isinstance(v, list):
        return v[0] if v else ""
    return v or ""


def main():
    days = int(sys.argv[1])
    out = sys.argv[2]
    today = datetime.date.today()
    since = (today - datetime.timedelta(days=days)).strftime("%Y%m%d")
    q = "buyer-country=ITA AND publication-date>=%s SORT BY publication-number DESC" % since
    page, got, total = 1, [], None
    while True:
        d = post({"query": q, "fields": FIELDS, "limit": 250, "page": page})
        ns = d.get("notices", [])
        total = d.get("totalNoticeCount", total)
        got.extend(ns)
        if len(ns) < 250 or len(got) >= 9000:
            break
        page += 1
        time.sleep(0.4)
    rows = []
    for n in got:
        nt = n.get("notice-type", "")
        if not nt.startswith("cn"):
            continue
        dls = [x[:10] for x in (n.get("deadline-receipt-tender-date-lot") or []) if x]
        dl = min(dls) if dls else ""
        if dl and dl < today.isoformat():
            continue
        cat, title = pick_title(n.get("notice-title"))
        vals = []
        for x in n.get("estimated-value-lot") or []:
            try:
                vals.append(float(x))
            except Exception:
                pass
        cpvs = sorted(set(n.get("classification-cpv") or []))
        pn = n["publication-number"]
        rows.append({
            "id": pn,
            "pubblicato": (n.get("publication-date") or "")[:10],
            "scadenza": dl,
            "tipo": nt,
            "ente": first(n.get("buyer-name")),
            "categoria": cat,
            "titolo": title,
            "cpv": cpvs,
            "valore_eur": round(sum(vals), 2) if vals else None,
            "link": "https://ted.europa.eu/it/notice/%s/html" % pn,
        })
    json.dump({"generato": today.isoformat(), "totale_avvisi_periodo": total,
               "scaricati": len(got), "bandi_aperti": len(rows), "rows": rows},
              open(out, "w"), ensure_ascii=False)
    print("periodo da", since, "| avvisi totali:", total, "| scaricati:", len(got),
          "| bandi con scadenza futura:", len(rows))


if __name__ == "__main__":
    main()
