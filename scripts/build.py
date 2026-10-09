"""Merge the research findings (research/round*/*.json by default) and the curated data/ files into ai_names.csv and site/index.html.

Run from anywhere: python3 scripts/build.py [folder-of-json-files]
"""
import csv, glob, json, re, sys
from pathlib import Path

here = Path(__file__).resolve().parent.parent  # repository root
pattern = str(Path(sys.argv[1]) / "*.json") if len(sys.argv) > 1 else str(here / "research" / "round*" / "*.json")
keys = ["name", "company", "project", "use", "category", "nameType", "source", "list", "gender", "funny", "pick", "launched", "launchBasis"]
norm = lambda s: re.sub(r"\W", "", s.lower())

rows, seen, dupes = [], {}, []
for f in sorted(glob.glob(pattern)):
    origin = "/".join(Path(f).parts[-2:])
    text = Path(f).read_text()
    text = text[text.index("["): text.rindex("]") + 1]
    for d in json.loads(text):
        d = {k: str(d.get(k) or "").strip() for k in keys}
        if not d["name"] or not d["company"]:
            continue
        d["nameType"] = "human" if d["nameType"].lower() == "human" else "brand"
        k = (norm(d["name"]), norm(d["company"])[:8])
        if k in seen:
            dupes.append((d["name"], d["company"], seen[k], origin))
            continue
        seen[k] = origin
        rows.append(d)

# Manual review: retired/renamed, duplicates across agents, weak or out-of-scope entries
DROP = {("Rufus", "Amazon"), ("Le Chat", "Mistral AI"), ("Harvey", "Harvey AI"),
        ("Magenta AI", "T-Mobile / Deutsche Telekom"), ("Olivia", "Paradox (used by McDonald's via McHire)"),
        ("Wenxiaoyan", "Baidu"), ("Celia (Xiaoyi)", "Huawei"), ("Ghostwriter", "Sierra"),
        ("Mia", "Moveworks"), ("Sara", "Emirates"),
        # Round 2: same AI under a second company spelling, or a generic word rather than a name
        ("JAX", "Xero"), ("AskDISHA 2.0", "IRCTC (Indian Railways)"), ("OZ", "Zong 4G"),
        ("Pixie", "Checkers (Shoprite Group)"), ("Concierge", "Expensify"),
        # Round 3: only source describes it as a 2024 proof of concept
        ("CHARLIE", "Air France"), ("AVA", "Dane County (Wisconsin)"),
        ("Bradley", "State of South Carolina (Department of Administration)"),
        ("Versa", "UCSF"), ("BruinChat", "University of California, Los Angeles"),
        # Round 4: the "name" is just the company's own brand name, not a separate AI persona
        # (round 5 restored the ones whose company has a human name; see AI_NATIVE below)
        ("BloomyBot", "Bloomy"), ("Dot", "GetDot"), ("Dash", "GovDash"), ("Centra", "Centralize"),
        # Round 5: product brands rather than personas or human-named companies
        ("Genie", "Databricks"), ("K Pro", "Owkin"), ("Claygent", "Clay"), ("Clu", "Cleanlist AI"), ("Hero", "Vivun"),
        ("Scout", "Valley"), ("LEXI", "Floatbot"), ("ADDI", "Floatbot"), ("Scout", "Floatbot"), ("Dentina", "Dentina"),
        ("Novi", "Savvy Agents"), ("KIKI", "Kickcall"), ("Dot", "Dot (getdot.ai)"), ("Jarmin", "Jarmin"),
        # Round 5: Tavus demo personas with the wrong company and YC tag, a partner's product, a plant app,
        # generic names, and entries the source could not confirm or that repeat another entry
        ("Piper", "Salesforce"), ("Aurora", "Orum"), ("Ruby", "Med Learning Group"), ("Vera", "Costco Wholesale"),
        ("Greg", "Greg"), ("Assist", "Motorola Solutions"), ("One Wealth Assistant", "Northern Trust"),
        ("Health Companion", "GE HealthCare"), ("Lea", "Leona Health"), ("Bob the Fixer", "SBA Communications"),
        ("CallJess", "CallJess")}
rows = [d for d in rows if (d["name"], d["company"]) not in DROP]

# Apply verified audit findings: retired AIs are dropped, renamed ones get the current name and source
for f in sorted(here.glob("research/audit*.json")):
    fixes = {(a["name"], a["company"]): a for a in json.loads(f.read_text())}
    for d in rows:
        a = fixes.get((d["name"], d["company"]))
        if a and a["action"] == "rename" and a.get("newName"):
            d["name"] = a["newName"]
        if a and a.get("newSource"):
            d["source"] = a["newSource"]
        if a and a.get("newUse"):
            d["use"] = a["newUse"]
    rows = [d for d in rows if fixes.get((d["name"], d["company"]), {}).get("action") != "drop"]
for d in rows:
    if d["name"] == "Joule":
        d["nameType"] = "brand"
    if d["name"] == "Olivia" and d["company"].startswith("Paradox"):
        d["use"] = d["use"].rstrip(".") + ". Used by McDonald's, among others."

# Collapse the agents' free-text industries into a short filter list (first match wins)
BUCKETS = [
    ("Airlines & Airports", ["airline", "airport"]),
    ("Travel & Hospitality", ["hotel", "cruise", "travel", "hospitality", "members", "rail", "theme park", "entertainment", "tourism", "resort", "casino"]),
    ("Automotive & Logistics", ["automotive", "logistics", "postal", "shipping"]),
    ("Insurance", ["insurance"]),
    ("Banking & Finance", ["bank", "credit union", "fintech", "invest", "wealth", "crypto", "accounting", "brokerage", "finance", "stock exchange"]),
    ("Government & Military", ["government", "military"]),
    ("Telecom & Utilities", ["telecom", "utilit", "energy"]),
    ("Healthcare & Pharma", ["health", "pharma", "hospital", "medical", "fitness", "wellness", "dental"]),
    ("Legal & Consulting", ["legal", "law", "consulting", "professional services"]),
    ("Education", ["educat", "edtech", "universit", "college", "school"]),
    ("Media, Sports & Culture", ["media", "news", "sport", "museum", "nonprofit", "gaming", "game", "church", "religio"]),
    ("Food & Restaurants", ["restaurant", "food", "coffee", "wine", "grocery", "supermarket", "beverage"]),
    ("Retail & E-commerce", ["retail", "commerce", "fashion", "beauty", "furniture", "home", "department", "pet", "luxury", "consumer goods", "consumer services", "real estate", "toy"]),
    ("AI Labs & Big Tech", ["ai lab", "big tech", "tech", "consumer ai", "consumer devices", "electronics", "internet", "browser", "dating"]),
    ("Industry & Manufacturing", ["aerospace", "manufactur", "semiconductor", "industrial", "chemical"]),
    ("Sales & Customer Service", ["sales", "customer service", "call center", "hr", "recruit"]),
    ("Business Software", ["software", "developer", "productivity", "workplace", "creative", "marketing", "cybersecurity"]),
]
for d in rows:
    c = d["category"].lower()
    d["category"] = next((b for b, keys in BUCKETS if any(k in c for k in keys)), "Other")

# Fortune 1000 / Y Combinator tags: round-4 entries carry their own, the rest come from the reviewed mapping
labels = json.loads((here / "data" / "list_labels.json").read_text())
for d in rows:
    d["list"] = d["list"] or labels.get(d["company"], "")
# Round-4 entries restored in round 5: human-named AI startups, tagged like the round-5 startups
AI_NATIVE = {("Avery", "AveryIQ"), ("Burt", "Burt"), ("Alice", "Alice.tech"), ("Bernard", "Bernard"), ("Luna", "LunaBill")}
for d in rows:
    if (d["name"], d["company"]) in AI_NATIVE and "AI-native startup" not in d["list"]:
        d["list"] = " · ".join(filter(None, ["AI-native startup", d["list"]]))

# Gender association of each name (feminine / masculine / neutral), reviewed in data/name_gender.json
genders = json.loads((here / "data" / "name_gender.json").read_text())
for d in rows:
    d["gender"] = genders.get(f'{d["name"]}|{d["company"]}', "")
missing = [d["name"] for d in rows if not d["gender"]]
if missing:
    print(f"no gender for {len(missing)}: {', '.join(missing[:20])}")

# How funny the name is, 0-3 (3 laugh-out-loud, 2 good pun or absurd persona, 1 mildly playful), from data/name_funny.json
funny = json.loads((here / "data" / "name_funny.json").read_text())
for d in rows:
    d["funny"] = str(funny.get(f'{d["name"]}|{d["company"]}', 0))

# Launch month (YYYY-MM, or YYYY when only the year is known) and whether it is the launch,
# announcement or earliest mention, researched per entry into data/launch_dates/*.json
launch = {}
for f in sorted(here.glob("data/launch_dates/*.json")):
    for a in json.loads(f.read_text()):
        if re.fullmatch(r"20\d\d(-[01]\d)?", a.get("launched") or ""):
            launch[f'{a["name"]}|{a["company"]}'] = a
for d in rows:
    a = launch.get(f'{d["name"]}|{d["company"]}', {})
    d["launched"], d["launchBasis"] = a.get("launched", ""), a.get("basis", "") if a else ""
print(f"launch date for {sum(bool(d['launched']) for d in rows)} of {len(rows)}")

# Editor's picks: hand-ordered list shown first in the page's default sort (1 = first), from data/editors_picks.json
picks = json.loads((here / "data" / "editors_picks.json").read_text())
for d in rows:
    k = f'{d["name"]}|{d["company"]}'
    d["pick"] = str(picks.index(k) + 1) if k in picks else ""
missing_picks = set(picks) - {f'{d["name"]}|{d["company"]}' for d in rows}
if missing_picks:
    print("editor's picks not found:", ", ".join(sorted(missing_picks)))

rows.sort(key=lambda d: d["name"].lower())

# Report what the automatic dedupe removed, and same-name entries left for manual review
for name, company, first, again in dupes:
    print(f"duplicate: {name} ({company}) in {again}, already in {first}")
words = lambda s: {w for w in re.findall(r"\w+", s.lower()) if len(w) > 3 and w not in {"bank", "group", "government"}}
by_name = {}
for d in rows:
    by_name.setdefault(norm(d["name"]), []).append(d["company"])
for n, cos in sorted(by_name.items()):
    if any(words(a) & words(b) for i, a in enumerate(cos) for b in cos[i + 1:]):
        print(f"check: {n}: {'; '.join(cos)}")
with open(here / "ai_names.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)

# ---- Page -------------------------------------------------------------------------------------
# src/template.html holds the page. Two outputs:
#   site/index.html      a complete standalone page for the website (everyainame.com), with search/social tags
#   build/artifact.html  the same page without the document wrapper, for the claude.ai artifact (its host adds one)
from html import escape
from urllib.parse import urlparse

SITE = "https://everyainame.com/"
MON = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

def launch_label(d):
    y, _, m = d["launched"].partition("-")
    when = f"{MON[int(m) - 1]} {y}" if m else y
    verb = {"announced": "Announced", "earliest mention": "By"}.get(d["launchBasis"], "Launched")
    return f"{verb} {when}"

def card(d):
    """Same markup as card() in src/template.html, so search engines see every name before any script runs."""
    e = lambda v: escape(v or "")
    host = (urlparse(d["source"]).hostname or "").removeprefix("www.")
    pills = (f'<span class="pill">{e(launch_label(d))}</span>' if d["launched"] else "") + f'<span class="pill">{e(d["category"])}</span>'
    pills += '<span class="pill human">Human name</span>' if d["nameType"] == "human" else ""
    pills += "".join(f'<span class="pill list">{e(l)}</span>' for l in d["list"].split(" · ") if l)
    pills += f'<a class="src" href="{e(d["source"])}" target="_blank" rel="noopener">{e(host)}</a>' if host else ""
    proj = f' <span class="proj">· {e(d["project"])}</span>' if d["project"] else ""
    return (f'<article class="tag"><div class="band"><b>HELLO</b><span>my name is</span></div><div class="name">{e(d["name"])}</div>'
            f'<div class="body"><div class="co">{e(d["company"])}{proj}</div><p class="use">{e(d["use"])}</p></div><div class="meta">{pills}</div></article>')

# Cards in the page's default order: Editor's Picks, then funniest, then A-Z
default_order = sorted(rows, key=lambda d: (0, int(d["pick"]), "") if d["pick"] else (1, 3 - int(d["funny"] or 0), d["name"].lower()))
tpl = (here / "src" / "template.html").read_text()
data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
body = re.sub(r"/\*DATA\*/.*?/\*END\*/", lambda m: data, tpl, flags=re.S)
body = body.replace("/*CARDS*/", "".join(card(d) for d in default_order))
(here / "build").mkdir(exist_ok=True)
(here / "build" / "artifact.html").write_text(body)

# Standalone page: move the template's leading <title>/<link>/<style> into <head> and add search and social tags
head, sep, rest = body.partition('<div class="wrap">')
title = "Every AI Name: Hello, My Name Is AI"
desc = (f"An incomplete catalog of {len(rows):,} named AI assistants, chatbots and agents, from Bank of America's Erica "
        "to Chipotle's Ava Cado. Search them all, sort by the funniest, and see who names their AI what.")
dataset = {
    "@context": "https://schema.org", "@type": "Dataset", "name": "Every AI Name", "url": SITE,
    "description": desc, "isAccessibleForFree": True, "license": "https://creativecommons.org/licenses/by/4.0/",
    "keywords": ["AI assistants", "chatbots", "AI agents", "product naming", "virtual assistants"],
    "creator": {"@type": "Person", "name": "Lukas Thoms", "url": "https://electriclantern.co"},
    "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": SITE + "ai_names.csv"}],
}
meta = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(desc)}">
<link rel="canonical" href="{SITE}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta name="theme-color" content="#d42a35">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE}">
<meta property="og:site_name" content="Every AI Name">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(desc)}">
<meta property="og:image" content="{SITE}og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(dataset, ensure_ascii=False)}</script>
"""
head = re.sub(r"<title>.*?</title>\n?", "", head, count=1, flags=re.S)
standalone = f'<!doctype html>\n<html lang="en">\n<head>\n{meta}{head.strip()}\n</head>\n<body>\n{sep}{rest}\n</body>\n</html>\n'
site = here / "site"
site.mkdir(exist_ok=True)
(site / "index.html").write_text(standalone)
__import__("shutil").copyfile(here / "ai_names.csv", site / "ai_names.csv")
(site / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n")
(site / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                  f'  <url><loc>{SITE}</loc><lastmod>{__import__("datetime").date.today()}</lastmod></url>\n</urlset>\n')
print(len(rows), "entries,", sum(d["nameType"] == "human" for d in rows), "human")
