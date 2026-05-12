#!/usr/bin/env python3
"""Market Update — run each morning to open your daily briefing."""

import datetime
import json
import os
import random
import re
import webbrowser
from pathlib import Path

import feedparser
import wikipedia
import yfinance as yf
from bs4 import BeautifulSoup

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

TICKERS = {
    "S&P 500":          "^GSPC",
    "Dow Jones":        "^DJI",
    "NASDAQ":           "^IXIC",
    "Gold":             "GC=F",
    "10-Yr Yield":      "^TNX",
    "Biotech (XBI)":    "XBI",
}

RSS_HEALTHCARE = [
    "https://www.biopharmadive.com/feeds/news/",
    "https://www.statnews.com/feed/",
    "https://endpts.com/feed/",
    "https://www.healthcaredive.com/feeds/news/",
    "https://www.fiercepharma.com/rss/xml",
    "https://www.fiercebiotech.com/rss/xml",
    "https://medcitynews.com/feed/",
]

RSS_FDA = [
    "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
    "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/fda-news/rss.xml",
]

RSS_MACRO = [
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    "https://finance.yahoo.com/rss/topstories",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
]

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

DEAL_KEYWORDS = [
    "acqui", "merger", "deal", "buys", "purchase", "takeover",
    "agreement", "transaction", "license", "partnership", "invest",
    "million", "billion", "collaboration", "divest",
]

HEALTHCARE_COMPANIES = [
    # Large Pharma
    ("Pfizer",                           "Large Pharma",          "https://www.pfizer.com"),
    ("Eli Lilly",                        "Large Pharma",          "https://www.lilly.com"),
    ("AbbVie",                           "Large Pharma",          "https://www.abbvie.com"),
    ("Merck",                            "Large Pharma",          "https://www.merck.com"),
    ("Bristol-Myers Squibb",             "Large Pharma",          "https://www.bms.com"),
    ("Johnson & Johnson",                "Large Pharma",          "https://www.jnj.com"),
    ("Novartis",                         "Large Pharma",          "https://www.novartis.com"),
    ("Roche",                            "Large Pharma",          "https://www.roche.com"),
    ("Sanofi",                           "Large Pharma",          "https://www.sanofi.com"),
    ("AstraZeneca",                      "Large Pharma",          "https://www.astrazeneca.com"),
    # Biotech
    ("Amgen",                            "Biotech",               "https://www.amgen.com"),
    ("Gilead Sciences",                  "Biotech",               "https://www.gilead.com"),
    ("Biogen",                           "Biotech",               "https://www.biogen.com"),
    ("Regeneron Pharmaceuticals",        "Biotech",               "https://www.regeneron.com"),
    ("Vertex Pharmaceuticals",           "Biotech",               "https://www.vrtx.com"),
    ("BioNTech",                         "Biotech",               "https://www.biontech.com"),
    ("Moderna",                          "Biotech",               "https://www.modernatx.com"),
    ("Alnylam Pharmaceuticals",          "Biotech",               "https://www.alnylam.com"),
    ("Exact Sciences",                   "Biotech",               "https://www.exactsciences.com"),
    ("Neurocrine Biosciences",           "Biotech",               "https://www.neurocrine.com"),
    ("Blueprint Medicines",              "Biotech",               "https://www.blueprintmedicines.com"),
    ("Intellia Therapeutics",            "Biotech",               "https://www.intelliatx.com"),
    # MedTech / Devices
    ("Medtronic",                        "MedTech",               "https://www.medtronic.com"),
    ("Abbott Laboratories",              "MedTech",               "https://www.abbott.com"),
    ("Boston Scientific",                "MedTech",               "https://www.bostonscientific.com"),
    ("Stryker",                          "MedTech",               "https://www.stryker.com"),
    ("Zimmer Biomet",                    "MedTech",               "https://www.zimmerbiomet.com"),
    ("Becton Dickinson",                 "MedTech",               "https://www.bd.com"),
    ("Hologic",                          "MedTech",               "https://www.hologic.com"),
    ("Intuitive Surgical",               "MedTech",               "https://www.intuitivesurgical.com"),
    ("Edwards Lifesciences",             "MedTech",               "https://www.edwards.com"),
    ("Insulet Corporation",              "MedTech",               "https://www.insulet.com"),
    # Managed Care / Health Services
    ("UnitedHealth Group",               "Managed Care",          "https://www.unitedhealthgroup.com"),
    ("CVS Health",                       "Health Services",       "https://www.cvshealth.com"),
    ("Cigna",                            "Managed Care",          "https://www.cigna.com"),
    ("Elevance Health",                  "Managed Care",          "https://www.elevancehealth.com"),
    ("HCA Healthcare",                   "Health Services",       "https://www.hcahealthcare.com"),
    ("Humana",                           "Managed Care",          "https://www.humana.com"),
    ("Molina Healthcare",                "Managed Care",          "https://www.molinahealthcare.com"),
    ("Tenet Healthcare",                 "Health Services",       "https://www.tenethealth.com"),
    # Healthtech / Digital Health
    ("Veeva Systems",                    "Healthtech",            "https://www.veeva.com"),
    ("Teladoc Health",                   "Digital Health",        "https://www.teladoc.com"),
    ("Evolent Health",                   "Digital Health",        "https://www.evolenthealth.com"),
    ("Alignment Healthcare",             "Digital Health",        "https://www.alignmenthealthcare.com"),
    # CRO / CDMO / Life Sciences Tools
    ("IQVIA",                            "CRO / Life Sciences",   "https://www.iqvia.com"),
    ("Charles River Laboratories",       "CRO / Life Sciences",   "https://www.criver.com"),
    ("Catalent",                         "CDMO",                  "https://www.catalent.com"),
    ("Thermo Fisher Scientific",         "Life Sciences Tools",   "https://www.thermofisher.com"),
    ("Danaher",                          "Life Sciences Tools",   "https://www.danaher.com"),
    ("Agilent Technologies",             "Life Sciences Tools",   "https://www.agilent.com"),
    # Diagnostics
    ("Quest Diagnostics",                "Diagnostics",           "https://www.questdiagnostics.com"),
    ("Laboratory Corporation of America","Diagnostics",           "https://www.labcorp.com"),
]

# ── DATA FETCHING ─────────────────────────────────────────────────────────────

def fetch_market_data():
    data = {}
    for name, ticker in TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if len(hist) >= 2:
                prev  = float(hist["Close"].iloc[-2])
                close = float(hist["Close"].iloc[-1])
                chg   = close - prev
                pct   = (chg / prev) * 100
                data[name] = {"price": close, "change": chg, "pct_change": pct}
            elif len(hist) == 1:
                close = float(hist["Close"].iloc[-1])
                data[name] = {"price": close, "change": 0.0, "pct_change": 0.0}
        except Exception as e:
            print(f"  [warn] {name}: {e}")
    return data


TICKER_COLORS = {
    "S&P 500": "#0d1d52",
    "XLV":     "#1a68c8",
    "XBI":     "#16a34a",
    "XHE":     "#d97706",
    "IHF":     "#7c3aed",
    "IHI":     "#0891b2",
    "XPH":     "#db2777",
}

def fetch_ytd_performance():
    """Fetch full YTD daily time-series (% return from Jan 1) for each ETF."""
    indices = [
        ("S&P 500", "^GSPC", True),
        ("XLV",     "XLV",   False),
        ("XBI",     "XBI",   False),
        ("XHE",     "XHE",   False),
        ("IHF",     "IHF",   False),
        ("IHI",     "IHI",   False),
        ("XPH",     "XPH",   False),
    ]
    year_start = f"{datetime.datetime.now().year}-01-01"
    series = []
    for name, ticker, is_benchmark in indices:
        try:
            hist = yf.Ticker(ticker).history(start=year_start)
            if len(hist) < 2:
                continue
            closes   = [float(p) for p in hist["Close"]]
            start_p  = closes[0]
            pct      = [round((p - start_p) / start_p * 100, 2) for p in closes]
            dates    = [d.strftime("%Y-%m-%d") for d in hist.index]
            series.append({
                "name":         name,
                "is_benchmark": is_benchmark,
                "ytd":          pct[-1],
                "dates":        dates,
                "values":       pct,
            })
        except Exception as e:
            print(f"  [warn] YTD {name}: {e}")
    return series


def fetch_rss(urls, limit=8):
    entries = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            source = feed.feed.get("title", url.split("/")[2])
            for entry in feed.entries[:limit]:
                summary = clean_html(entry.get("summary", entry.get("description", "")))
                entries.append({
                    "title":   entry.get("title", "").strip(),
                    "summary": summary,
                    "link":    entry.get("link", "#"),
                    "source":  source,
                })
        except Exception as e:
            print(f"  [warn] RSS {url}: {e}")
    return entries


def clean_html(text):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    plain = soup.get_text(separator=" ").strip()
    plain = re.sub(r"\s+", " ", plain)
    return plain[:350]


MA_KEYWORDS = ["acqui", "merger", "buys", "takeover", "divest", "spin-off", "buyout", "purchase"]

def find_deals(entries, n=2):
    """Return the top n deal candidates, prioritizing M&A over partnerships/licensing."""
    scored = []
    for e in entries:
        combined = (e["title"] + " " + e["summary"]).lower()
        score = sum(1 for kw in DEAL_KEYWORDS if kw in combined)
        # Strong boost for M&A specifically
        if any(kw in combined for kw in MA_KEYWORDS):
            score += 4
        # Boost for deal size mentions
        if re.search(r"\$[\d,.]+\s*(million|billion|bn|mn)", combined):
            score += 3
        if score > 0:
            scored.append((score, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    # Deduplicate by title similarity
    seen, results = [], []
    for _, e in scored:
        if not any(e["title"][:40] in s for s in seen):
            seen.append(e["title"][:40])
            results.append(e)
        if len(results) == n:
            break
    return results


def fetch_company_spotlight():
    company, vertical, website = random.choice(HEALTHCARE_COMPANIES)
    try:
        wikipedia.set_lang("en")
        summary = wikipedia.summary(company, sentences=5, auto_suggest=False)
    except wikipedia.exceptions.DisambiguationError as e:
        try:
            summary = wikipedia.summary(e.options[0], sentences=5)
        except Exception:
            summary = f"{company} is a major healthcare company operating in the {vertical} space."
    except Exception:
        summary = f"{company} is a major healthcare company operating in the {vertical} space."
    return {"name": company, "vertical": vertical, "summary": summary, "url": website}


# ── AI MARKET NARRATIVE (Groq) ────────────────────────────────────────────────

def generate_market_narrative(market_data, macro_entries):
    """Call Groq to produce a structured, themed market rundown."""
    api_key = os.environ.get("GROQ_API_KEY") or GROQ_API_KEY
    if not api_key:
        return None
    try:
        from groq import Groq
    except ImportError:
        print("  [warn] groq not installed — run: pip install groq")
        return None

    market_str = "\n".join(
        f"{name}: {d['price']:.2f} ({'+' if d['pct_change'] >= 0 else ''}{d['pct_change']:.2f}%)"
        for name, d in market_data.items()
    )
    headlines = "\n".join(
        f"- {e['title']}: {e['summary'][:160]}"
        for e in macro_entries[:18] if e.get("title")
    )

    prompt = f"""You are a senior analyst at a healthcare investment bank writing a daily pre-market brief.

Based on the market data and headlines below, write a concise market rundown.

Market Data (yesterday's close):
{market_str}

Top News Headlines:
{headlines}

Return ONLY valid JSON in this exact structure (no markdown, no code fences):
{{
  "sections": [
    {{
      "title": "Market Update",
      "bullets": [
        "One sentence on overall market direction and magnitude with key index levels",
        "One sentence on which sectors led or lagged and what it signals about risk appetite",
        "One sentence on bond yield move and what it reflects about rate expectations",
        "One sentence on commodities move (oil, gold) and what it signals",
        "One sentence on dollar/FX move and what it suggests about macro sentiment"
      ]
    }}
  ]
}}

Rules: present tense, active voice, professional sell-side analyst tone, be specific with numbers from the market data, each bullet is exactly one sentence."""

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1400,
        )
        text = resp.choices[0].message.content.strip()
        # Strip code fences if the model includes them anyway
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
        return json.loads(text).get("sections")
    except Exception as e:
        print(f"  [warn] Groq narrative failed: {e}")
        return None


def generate_healthcare_verticals(hc_entries, fda_entries):
    """Generate the 4-vertical healthcare sector analysis using Groq."""
    api_key = os.environ.get("GROQ_API_KEY") or GROQ_API_KEY
    if not api_key:
        return None
    try:
        from groq import Groq
    except ImportError:
        return None

    headlines = "\n".join(
        f"- {e['title']}: {e['summary'][:180]}"
        for e in (hc_entries + fda_entries)[:25] if e.get("title")
    )

    prompt = f"""You are a senior healthcare investment banker at a boutique advisory firm. Write a daily sector update covering four verticals. Use today's headlines as context, supplementing with your knowledge of current conditions where headlines are thin.

Headlines:
{headlines}

For each vertical, follow this exact 3-part structure:
1. One sentence on the key development or current state
2. One sentence on the trend
3. One sentence on the M&A impact — what this means for deal activity, valuations, or strategy

Return ONLY valid JSON (no markdown, no code fences):
{{
  "verticals": [
    {{
      "name": "Payors & Payor Solutions",
      "summary": "one sentence on managed care, Medicare Advantage, PBMs, or payor earnings/guidance",
      "trend": "one sentence on margin pressure, utilization trends, or regulatory scrutiny",
      "ib_take": "one sentence on what this means for M&A, consolidation, or sponsor interest"
    }},
    {{
      "name": "Providers & Provider Solutions",
      "summary": "one sentence on hospital systems, physician groups, outpatient platforms, or reimbursement",
      "trend": "one sentence on consolidation, labor costs, or policy tailwinds/headwinds",
      "ib_take": "one sentence on deal flow outlook, sponsor appetite, or valuation dynamics"
    }},
    {{
      "name": "Government-Sponsored Programs",
      "summary": "one sentence on Medicare, Medicaid, VA, or relevant policy/regulatory update",
      "trend": "one sentence on funding shifts, compliance requirements, or cost containment",
      "ib_take": "one sentence on how policy changes affect deal activity or sector positioning"
    }},
    {{
      "name": "Medical Products / Life Sciences",
      "summary": "one sentence on biotech, pharma, devices, or diagnostics — FDA news, licensing, or big pharma strategy",
      "trend": "one sentence on where capital is flowing or what asset types are in demand",
      "ib_take": "one sentence on M&A premiums, licensing deal dynamics, or pipeline valuations"
    }}
  ]
}}"""

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1100,
        )
        text = resp.choices[0].message.content.strip()
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
        m2 = re.search(r"\{[\s\S]*\}", text)
        if m2:
            text = m2.group(0)
        return json.loads(text).get("verticals")
    except Exception as e:
        print(f"  [warn] Groq verticals failed: {e}")
        return None


def generate_macro_narrative(macro_entries):
    """Use Groq to produce a tight, IB-style macro update in prose paragraph format."""
    api_key = os.environ.get("GROQ_API_KEY") or GROQ_API_KEY
    if not api_key:
        return None
    try:
        from groq import Groq
    except ImportError:
        return None

    headlines = "\n".join(
        f"- {e['title']}: {e['summary'][:180]}"
        for e in macro_entries[:20] if e.get("title")
    )

    prompt = f"""You are a senior analyst at a healthcare investment bank writing a tight, forward-looking macro brief for a colleague skimming it at 7am.

Using the headlines below as context (supplement with your knowledge of current macro conditions where headlines are thin), write four short sections. Each section is 2-3 sentences max. Be interpretive and forward-looking — not just describing what happened, but what it means for markets and rates. Use language like "signals", "suggests", "remains at risk", "likely to", "points to".

Headlines:
{headlines}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "sections": [
    {{
      "title": "Fed / Rates",
      "bullets": ["one forward-looking sentence covering Fed stance, rate path, and yield curve signal"]
    }},
    {{
      "title": "Inflation",
      "bullets": ["one sentence on where core inflation stands and what it means for Fed policy"]
    }},
    {{
      "title": "Labor Market",
      "bullets": ["one sentence on employment conditions and how they affect the rate outlook"]
    }},
    {{
      "title": "Growth & Markets",
      "bullets": ["one sentence on GDP trajectory, recession risk, and credit conditions"]
    }}
  ],
  "summary": "2-3 sentence overall macroeconomic summary — synthesize the above into a plain-English view of where the economy stands and what it means for markets and deal activity"
}}"""

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=900,
        )
        text = resp.choices[0].message.content.strip()
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
        m2 = re.search(r"\{[\s\S]*\}", text)
        if m2:
            text = m2.group(0)
        parsed = json.loads(text)
        return {"sections": parsed.get("sections", []), "summary": parsed.get("summary", "")}
    except Exception as e:
        print(f"  [warn] Groq macro narrative failed: {e}")
        return None


# ── MARKET SUMMARY TEMPLATE (fallback) ───────────────────────────────────────

def build_market_summary(d):
    if not d:
        return "Market data is currently unavailable."

    def pct(key):
        return d.get(key, {}).get("pct_change", 0.0)

    def fmt(val):
        return f"{abs(val):.2f}%"

    def dir_word(val, up="gained", dn="fell"):
        return up if val >= 0 else dn

    sp = pct("S&P 500");  dj = pct("Dow Jones");  nq = pct("NASDAQ")
    xbi = pct("Biotech (XBI)");  gold = pct("Gold")

    s1 = (
        f"The S&P 500 {dir_word(sp)} {fmt(sp)} yesterday, "
        f"with the Dow Jones {dir_word(dj, 'up', 'down')} {fmt(dj)} "
        f"and the NASDAQ {dir_word(nq, 'advancing', 'declining')} {fmt(nq)}."
    )

    rel = "outperformed" if xbi > sp else "underperformed"
    s2 = (
        f"The small-cap biotech index (XBI) {rel} the broader market, "
        f"{dir_word(xbi, 'rising', 'falling')} {fmt(xbi)}, "
        f"while gold {dir_word(gold, 'climbed', 'slipped')} {fmt(gold)}."
    )
    return f"{s1} {s2}"


# ── HTML GENERATION ───────────────────────────────────────────────────────────

def fmt_price(name, price):
    if name == "10-Yr Yield":
        return f"{price:.3f}%"
    if name == "Gold":
        return f"${price:,.2f}"
    if "Yield" in name:
        return f"{price:.3f}%"
    return f"{price:,.2f}"


def ticker_cards_html(market_data):
    cards = []
    for name, d in market_data.items():
        pct = d["pct_change"]
        cls = "pos" if pct >= 0 else "neg"
        arrow = "▲" if pct >= 0 else "▼"
        cards.append(f"""
        <div class="ticker-card">
          <div class="tk-name">{name}</div>
          <div class="tk-price">{fmt_price(name, d['price'])}</div>
          <div class="tk-chg {cls}">{arrow} {abs(pct):.2f}%</div>
        </div>""")
    return "\n".join(cards)


def strip_label(text, *labels):
    """Remove any leading 'Label:' prefix the model may have baked into the value."""
    for label in labels:
        text = re.sub(rf"^{re.escape(label)}\s*:\s*", "", text, flags=re.IGNORECASE)
    return text.strip()

INDEX_DESCRIPTIONS = {
    "S&P 500": "Broad U.S. large-cap equity benchmark (500 companies)",
    "XLV":     "Health Care Select Sector SPDR — broad large-cap healthcare",
    "XBI":     "SPDR S&P Biotech — small/mid-cap biotech companies",
    "XHE":     "SPDR S&P Health Care Equipment — medical equipment & devices",
    "IHF":     "iShares U.S. Healthcare Providers — hospitals, managed care & insurers",
    "IHI":     "iShares U.S. Medical Devices — large-cap medical device companies",
    "XPH":     "SPDR S&P Pharmaceuticals — pharmaceutical manufacturers",
}

def sector_indices_html(ytd_data):
    """Render a multi-line YTD time-series chart + key table."""
    if not ytd_data:
        return '<p class="empty">Index data unavailable.</p>'

    sp500_ytd   = next((d["ytd"] for d in ytd_data if d["is_benchmark"]), 0)
    benchmark   = [d for d in ytd_data if d["is_benchmark"]]
    rest        = sorted([d for d in ytd_data if not d["is_benchmark"]], key=lambda x: x["ytd"], reverse=True)
    sorted_data = benchmark + rest

    # Build Chart.js datasets
    datasets = []
    for d in sorted_data:
        color     = TICKER_COLORS.get(d["name"], "#999999")
        is_bench  = d["is_benchmark"]
        point_data = [{"x": date, "y": val} for date, val in zip(d["dates"], d["values"])]
        datasets.append({
            "label":           d["name"],
            "data":            point_data,
            "borderColor":     color,
            "backgroundColor": color,
            "borderWidth":     2 if is_bench else 1.8,
            "borderDash":      [6, 4] if is_bench else [],
            "pointRadius":     0,
            "pointHoverRadius": 4,
            "tension":         0.3,
            "fill":            False,
        })
    datasets_json = json.dumps(datasets)

    # Key table
    key_rows = ""
    for d in sorted_data:
        ytd     = d["ytd"]
        color   = TICKER_COLORS.get(d["name"], "#999")
        val_cls = "kpos" if ytd >= 0 else "kneg"
        val_str = f"+{ytd:.1f}%" if ytd >= 0 else f"{ytd:.1f}%"
        vs_sp   = ytd - sp500_ytd
        vs_cell = "" if d["is_benchmark"] else f'<span class="{"kpos" if vs_sp >= 0 else "kneg"}">{("+" if vs_sp >= 0 else "")}{vs_sp:.1f}%</span>'
        desc    = INDEX_DESCRIPTIONS.get(d["name"], "")
        key_rows += f"""<tr>
          <td><span class="kdot" style="background:{color}"></span><strong>{d['name']}</strong></td>
          <td class="{val_cls} kval">{val_str}</td>
          <td class="kvs">{vs_cell}</td>
          <td class="kdesc">{desc}</td>
        </tr>"""

    return f"""
    <div style="position:relative;height:300px">
      <canvas id="ytdChart"></canvas>
    </div>
    <div class="idx-key">
      <table class="key-table">
        <thead><tr><th>Index</th><th>YTD</th><th>vs S&amp;P 500</th><th>Tracks</th></tr></thead>
        <tbody>{key_rows}</tbody>
      </table>
    </div>
    <script>
    (function(){{
      new Chart(document.getElementById('ytdChart'), {{
        type: 'line',
        data: {{ datasets: {datasets_json} }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          interaction: {{ mode: 'index', intersect: false }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              callbacks: {{
                label: c => ' ' + c.dataset.label + ': ' + (c.raw.y >= 0 ? '+' : '') + c.raw.y.toFixed(1) + '%'
              }}
            }}
          }},
          scales: {{
            x: {{
              type: 'time',
              time: {{ unit: 'month', displayFormats: {{ month: "MMM 'YY" }} }},
              grid: {{ display: false }},
              ticks: {{ font: {{ size: 11 }}, color: '#6b7280' }}
            }},
            y: {{
              grid: {{ color: 'rgba(0,0,0,0.05)' }},
              ticks: {{
                callback: v => (v >= 0 ? '+' : '') + v.toFixed(0) + '%',
                font: {{ size: 11 }},
                color: '#6b7280'
              }}
            }}
          }}
        }}
      }});
    }})();
    </script>"""


def verticals_html(verticals):
    if not verticals:
        return '<p class="empty">Sector analysis unavailable.</p>'
    cards = []
    for v in verticals:
        trend   = strip_label(v.get('trend', ''),   'Trend')
        ib_take = strip_label(v.get('ib_take', ''), 'IB Take', 'IB', 'M&A Impact')
        cards.append(f"""
    <div class="vert-card">
      <div class="vert-name">{v['name']}</div>
      <p class="vert-summary">{v.get('summary', '')}</p>
      <div class="vert-row">
        <span class="vert-label">Trend</span>
        <span class="vert-text">{trend}</span>
      </div>
      <div class="vert-row">
        <span class="vert-label ib-label">M&amp;A Impact</span>
        <span class="vert-text vert-ib">{ib_take}</span>
      </div>
    </div>""")
    return f'<div class="verticals-grid">{"".join(cards)}</div>'


def macro_prose_html(sections):
    """Render macro sections as titled prose paragraphs (not bullets)."""
    parts = []
    for i, sec in enumerate(sections):
        divider = "" if i == 0 else '<div class="narr-divider"></div>'
        parts.append(f"""{divider}
    <div class="macro-sec">
      <div class="macro-title">{sec['title']}</div>
      <p class="macro-body">{sec.get('body', '')}</p>
    </div>""")
    return "\n".join(parts)


def market_narrative_html(sections):
    """Render the AI-generated themed narrative sections."""
    parts = []
    for i, sec in enumerate(sections):
        bullets = "".join(f"<li>{b}</li>" for b in sec.get("bullets", []))
        divider = "" if i == 0 else '<div class="narr-divider"></div>'
        parts.append(f"""{divider}
    <div class="narr-sec">
      <div class="narr-title">{sec['title']}</div>
      <ul class="narr-bullets">{bullets}</ul>
    </div>""")
    return "\n".join(parts)


def market_bullets_html(entries, limit=3):
    """Top macro headlines as bullet points below the market summary."""
    if not entries:
        return ""
    items = "".join(
        f'<li><a class="bullet-link" href="{e["link"]}" target="_blank">{e["title"]}</a></li>'
        for e in entries[:limit] if e.get("title")
    )
    return f'<ul class="mkt-bullets">{items}</ul>'


def news_items_html(entries, limit=4):
    if not entries:
        return '<p class="empty">No items found.</p>'
    html = []
    for e in entries[:limit]:
        title = e["title"] or "Untitled"
        html.append(f"""
        <div class="news-item">
          <a class="ni-title" href="{e['link']}" target="_blank">{title}</a>
          <div class="ni-source">{e['source']}</div>
          <div class="ni-summary">{e['summary']}</div>
        </div>""")
    return "\n".join(html)


def deals_html(deals):
    if not deals:
        return '<p class="empty">No deal activity identified — check sources directly.</p>'
    parts = []
    for i, deal in enumerate(deals):
        divider = '<div class="deal-divider"></div>' if i > 0 else ""
        parts.append(f"""{divider}
    <div class="deal-card">
      <div class="deal-title">{deal['title']}</div>
      <div class="deal-source">{deal['source']}</div>
      <div class="deal-body">{deal['summary']}</div>
      <a class="more-link" href="{deal['link']}" target="_blank">Read full story →</a>
    </div>""")
    return "\n".join(parts)


def company_html(c):
    return f"""
    <div class="company-card">
      <div class="co-vertical">{c['vertical']}</div>
      <div class="co-name">{c['name']}</div>
      <div class="co-body">{c['summary']}</div>
      <a class="more-link" href="{c['url']}" target="_blank">Visit website →</a>
    </div>"""


def generate_html(market_data, summary, hc_entries, fda_entries, deals, macro_entries, company, narrative=None, macro_narrative=None, hc_verticals=None, ytd_data=None):
    today     = datetime.datetime.now().strftime("%A, %B %d, %Y")
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%B %d, %Y")
    generated = datetime.datetime.now().strftime("%I:%M %p")

    # Combine & deduplicate healthcare + FDA, exclude deals already shown
    all_hc = hc_entries + fda_entries
    all_hc = [e for e in all_hc if e not in deals]

    css = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
      background: #eef0f4;
      color: #111827;
      min-height: 100vh;
    }

    /* ─── HEADER ─── */
    .header {
      background: linear-gradient(135deg, #0c1d52 0%, #1c3e82 100%);
      border-bottom: 3px solid #1a68c8;
      padding: 28px 48px;
    }
    .header-inner {
      max-width: 1140px;
      margin: 0 auto;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }
    .brand { color: #fff; }
    .brand h1 { font-size: 26px; font-weight: 700; letter-spacing: -.4px; }
    .brand .sub { font-size: 13px; color: #8ab6d9; margin-top: 3px; }
    .datebox { text-align: right; }
    .datebox .date  { font-size: 14px; font-weight: 700; color: #1a68c8; }
    .datebox .stamp { font-size: 12px; color: #8ab6d9; margin-top: 4px; }

    /* ─── LAYOUT ─── */
    .wrap {
      max-width: 1140px;
      margin: 0 auto;
      padding: 32px 24px 48px;
    }

    .section {
      background: #fff;
      border-radius: 12px;
      padding: 28px 32px;
      margin-bottom: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,.07), 0 4px 16px rgba(0,0,0,.04);
      border: 1px solid #e3e7ed;
    }

    .sec-head {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 22px;
      padding-bottom: 14px;
      border-bottom: 1px solid #eef0f4;
    }
    .sec-num {
      background: #0d1d52;
      color: #1a68c8;
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 1px;
      padding: 3px 7px;
      border-radius: 4px;
    }
    .sec-title {
      font-size: 13px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .8px;
      color: #0d1d52;
    }

    /* ─── MARKET TICKERS ─── */
    .ticker-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      gap: 12px;
      margin-bottom: 22px;
    }
    .ticker-card {
      background: #f8f9fb;
      border: 1px solid #e3e7ed;
      border-radius: 10px;
      padding: 14px 16px;
      text-align: center;
    }
    .tk-name  { font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }
    .tk-price { font-size: 19px; font-weight: 700; color: #0d1d52; margin-bottom: 4px; }
    .tk-chg   { font-size: 13px; font-weight: 700; }
    .pos { color: #15803d; }
    .neg { color: #dc2626; }

    .mkt-summary {
      border-left: 4px solid #1a68c8;
      background: #f0f5ff;
      padding: 16px 20px;
      border-radius: 0 8px 8px 0;
      font-size: 14.5px;
      line-height: 1.75;
      color: #374151;
    }

    /* ─── AI NARRATIVE ─── */
    .narr-sec { margin-bottom: 4px; }
    .narr-title {
      font-size: 13px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .7px;
      color: #0d1d52;
      margin-bottom: 10px;
      margin-top: 18px;
    }
    .narr-sec:first-child .narr-title { margin-top: 0; }
    .narr-bullets {
      list-style: none;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 7px;
    }
    .narr-bullets li {
      display: flex;
      align-items: flex-start;
      gap: 9px;
      font-size: 13.5px;
      color: #374151;
      line-height: 1.55;
    }
    .narr-bullets li::before {
      content: "–";
      color: #1a68c8;
      font-weight: 800;
      flex-shrink: 0;
      margin-top: 1px;
    }
    .narr-divider {
      height: 1px;
      background: #eef0f4;
      margin: 16px 0 0;
    }

    /* ─── SECTOR INDICES ─── */
    .idx-key { margin-top: 24px; }
    .key-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .key-table th {
      text-align: left;
      font-size: 10.5px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .6px;
      color: #6b7280;
      padding: 0 16px 10px 0;
      border-bottom: 2px solid #eef0f4;
    }
    .key-table td { padding: 9px 16px 9px 0; border-bottom: 1px solid #f5f7fa; vertical-align: middle; }
    .key-table tbody tr:last-child td { border-bottom: none; }
    .kdot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; vertical-align: middle; flex-shrink: 0; }
    .kval { font-weight: 800; white-space: nowrap; }
    .kpos { color: #15803d; }
    .kneg { color: #dc2626; }
    .kvs  { font-size: 12px; font-weight: 600; white-space: nowrap; }
    .kdesc { color: #6b7280; font-size: 12.5px; }

    /* ─── HEALTHCARE VERTICALS ─── */
    .verticals-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .vert-card {
      background: #f8f9fb;
      border: 1px solid #e3e7ed;
      border-top: 3px solid #1a68c8;
      border-radius: 0 0 10px 10px;
      padding: 18px 20px;
    }
    .vert-name {
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .7px;
      color: #0d1d52;
      margin-bottom: 10px;
    }
    .vert-summary {
      font-size: 13px;
      color: #374151;
      line-height: 1.6;
      margin-bottom: 12px;
    }
    .vert-row {
      margin-bottom: 10px;
    }
    .vert-row:last-child { margin-bottom: 0; }
    .vert-label {
      display: block;
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .7px;
      color: #6b7280;
      margin-bottom: 3px;
    }
    .vert-text {
      font-size: 13px;
      color: #374151;
      line-height: 1.55;
    }
    .ib-label { color: #1a68c8; }
    .vert-ib  { color: #0d1d52; font-weight: 600; }

    @media (max-width: 800px) {
      .verticals-grid { grid-template-columns: 1fr; }
    }

    /* ─── MACRO PROSE ─── */
    .macro-sec { margin-bottom: 4px; }
    .macro-title {
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: .8px;
      color: #0d1d52;
      margin-bottom: 7px;
      margin-top: 18px;
    }
    .macro-sec:first-child .macro-title { margin-top: 0; }
    .macro-body {
      font-size: 13.5px;
      color: #374151;
      line-height: 1.7;
    }

    .macro-summary {
      margin-top: 20px;
      padding-top: 16px;
      border-top: 1px solid #eef0f4;
      font-size: 13.5px;
      color: #374151;
      line-height: 1.7;
      font-style: italic;
    }

    /* ─── FALLBACK BULLETS (no API key) ─── */
    .mkt-bullets {
      list-style: none;
      margin-top: 14px;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .mkt-bullets li {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      font-size: 13.5px;
      color: #374151;
      line-height: 1.5;
    }
    .mkt-bullets li::before {
      content: "–";
      color: #1a68c8;
      font-weight: 700;
      flex-shrink: 0;
      margin-top: 1px;
    }
    .bullet-link {
      color: #0d1d52;
      text-decoration: none;
      font-weight: 500;
    }
    .bullet-link:hover { text-decoration: underline; }

    /* ─── TWO-COL ─── */
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }

    /* ─── NEWS ─── */
    .news-item {
      padding: 16px 0;
      border-bottom: 1px solid #f0f2f5;
    }
    .news-item:last-child { border-bottom: none; }
    .ni-title  { display: block; font-size: 14.5px; font-weight: 600; color: #0d1d52; text-decoration: none; line-height: 1.45; margin-bottom: 4px; }
    .ni-title:hover { text-decoration: underline; color: #1a4080; }
    .ni-source { font-size: 10.5px; font-weight: 800; text-transform: uppercase; letter-spacing: .6px; color: #1a68c8; margin-bottom: 6px; }
    .ni-summary { font-size: 13px; color: #6b7280; line-height: 1.55; }

    /* ─── DEAL ─── */
    .deal-card {
      background: linear-gradient(135deg, #f5f7fa 0%, #eaeff6 100%);
      border: 1px solid #d1dbe7;
      border-radius: 10px;
      padding: 22px 24px;
    }
    .deal-title  { font-size: 17px; font-weight: 700; color: #0d1d52; line-height: 1.4; margin-bottom: 6px; }
    .deal-source { font-size: 10.5px; font-weight: 800; text-transform: uppercase; letter-spacing: .6px; color: #1a68c8; margin-bottom: 14px; }
    .deal-body   { font-size: 13.5px; color: #374151; line-height: 1.7; margin-bottom: 16px; }
    .deal-divider { height: 1px; background: #d1dbe7; margin: 20px 0; }

    /* ─── COMPANY ─── */
    .company-card {
      background: linear-gradient(135deg, #f5f7fa 0%, #eaeff6 100%);
      border: 1px solid #d1dbe7;
      border-radius: 10px;
      padding: 24px 28px;
    }
    .co-vertical { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .8px; color: #1a68c8; margin-bottom: 6px; }
    .co-name     { font-size: 26px; font-weight: 800; color: #0d1d52; margin-bottom: 16px; }
    .co-body     { font-size: 14px; color: #374151; line-height: 1.8; margin-bottom: 18px; }

    .more-link {
      font-size: 13px;
      font-weight: 700;
      color: #1a4080;
      text-decoration: none;
      border-bottom: 1.5px solid #1a4080;
      padding-bottom: 1px;
    }
    .more-link:hover { color: #0d1d52; border-color: #0d1d52; }

    .empty { color: #9ca3af; font-style: italic; font-size: 14px; text-align: center; padding: 20px; }

    /* ─── FOOTER ─── */
    .footer {
      text-align: center;
      padding: 20px;
      font-size: 11.5px;
      color: #9ca3af;
      border-top: 1px solid #e3e7ed;
      margin-top: 8px;
    }

    @media (max-width: 800px) {
      .two-col { grid-template-columns: 1fr; }
      .header { padding: 20px 24px; }
      .header-inner { flex-direction: column; gap: 12px; }
      .datebox { text-align: left; }
      .section { padding: 20px; }
    }
    """

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Market Update — {today}</title>
  <style>{css}</style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <div class="brand">
      <h1>Market Update</h1>
      <div class="sub">Daily Market &amp; Sector Intelligence</div>
    </div>
    <div class="datebox">
      <div class="date">{today}</div>
      <div class="stamp">Data as of close · {yesterday}</div>
    </div>
  </div>
</div>

<div class="wrap">

  <!-- 01 Market Update -->
  <div class="section">
    <div class="sec-head">
      <div class="sec-num">01</div>
      <div class="sec-title">Quick Market Update</div>
    </div>
    <div class="ticker-grid">
      {ticker_cards_html(market_data)}
    </div>
    {market_narrative_html(narrative) if narrative else
     f'<div class="mkt-summary">{summary}</div>{market_bullets_html(macro_entries)}'}
  </div>

  <!-- 02 Healthcare Verticals -->
  <div class="section">
    <div class="sec-head">
      <div class="sec-num">02</div>
      <div class="sec-title">Healthcare Sector Update</div>
    </div>
    {verticals_html(hc_verticals) if hc_verticals else news_items_html(all_hc, limit=5)}
  </div>

  <!-- 03 Recent Deals -->
  <div class="section">
    <div class="sec-head">
      <div class="sec-num">03</div>
      <div class="sec-title">Recent Deals</div>
    </div>
    {deals_html(deals)}
  </div>

  <!-- 04 Healthcare Indices YTD -->
  <div class="section">
    <div class="sec-head">
      <div class="sec-num">04</div>
      <div class="sec-title">Healthcare Indices — YTD vs S&amp;P 500</div>
    </div>
    {sector_indices_html(ytd_data)}
  </div>

  <!-- 05 Macro Update -->
  <div class="section">
    <div class="sec-head">
      <div class="sec-num">05</div>
      <div class="sec-title">Macro Update</div>
    </div>
    {(market_narrative_html(macro_narrative["sections"]) + f'<div class="macro-summary">{macro_narrative["summary"]}</div>') if macro_narrative else news_items_html(macro_entries, limit=4)}
  </div>

  <!-- 06 Company Spotlight -->
  <div class="section">
    <div class="sec-head">
      <div class="sec-num">06</div>
      <div class="sec-title">Company Spotlight</div>
    </div>
    {company_html(company)}
  </div>

</div>

<div class="footer">
  Market Update &nbsp;·&nbsp; Generated {generated} &nbsp;·&nbsp; For personal use only
</div>

</body>
</html>"""
    return body


# ── MAIN ──────────────────────────────────────────────────────────────────────

def generate():
    """Generate and return the brief as an HTML string. Used by the web app."""
    print("Market Update")
    print("=" * 40)

    print("Fetching market data...")
    market_data = fetch_market_data()
    summary = build_market_summary(market_data)

    print("Fetching YTD index performance...")
    ytd_data = fetch_ytd_performance()

    print("Fetching healthcare & FDA news...")
    hc_entries  = fetch_rss(RSS_HEALTHCARE, limit=6)
    fda_entries = fetch_rss(RSS_FDA, limit=4)

    print("Fetching macro news...")
    macro_entries = fetch_rss(RSS_MACRO, limit=6)

    print("Identifying recent deals...")
    deals = find_deals(hc_entries, n=2)

    print("Generating healthcare sector verticals...")
    hc_verticals = generate_healthcare_verticals(hc_entries, fda_entries)
    if hc_verticals:
        print("  ✓ Sector verticals ready")

    print("Loading company spotlight...")
    company = fetch_company_spotlight()

    print("Generating market narrative...")
    narrative = generate_market_narrative(market_data, macro_entries)
    if narrative:
        print("  ✓ Market narrative ready")
    else:
        print("  – No Groq key, using template fallback")

    print("Generating macro narrative...")
    macro_narrative = generate_macro_narrative(macro_entries)
    if macro_narrative:
        print("  ✓ Macro narrative ready")

    print("Generating brief...")
    return generate_html(
        market_data=market_data,
        summary=summary,
        hc_entries=hc_entries,
        fda_entries=fda_entries,
        deals=deals,
        macro_entries=macro_entries,
        company=company,
        narrative=narrative,
        macro_narrative=macro_narrative,
        hc_verticals=hc_verticals,
        ytd_data=ytd_data,
    )


def main():
    """Local use: generate brief, save to file, open in browser."""
    html = generate()
    out = Path.home() / "healthcare_brief.html"
    out.write_text(html, encoding="utf-8")
    print(f"Saved → {out}")
    webbrowser.open(f"file://{out}")
    print("Opened in browser. Good morning!")


if __name__ == "__main__":
    main()
