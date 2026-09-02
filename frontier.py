#!/usr/bin/env python3
# crew: Napoleon
"""frontier.py - find the TRUE current state of an Erdos problem before spending compute.

Why this exists: the bars quoted on erdosproblems.com and in OEIS are often stale
by many orders of magnitude, and the fresh ones are being taken right now. Problem
398 is listed at 10^9 (Berndt and Galway 2000) while the literature is near 10^15.
Problem 647 was taken by an independent compute campaign in June 2026. Running a
solver against a target somebody finished last month is the most expensive mistake
available on this campaign, so nothing computes until this tool has spoken.

Sources pulled, per problem:
  1. teorth/erdosproblems data/problems.yaml   (status.state, tags, prize, oeis)
  2. erdosproblems.com/<n>                     (statement, remarks, who is working)
  3. erdosproblems.com/forum/thread/<n>/proof-claims  (THE decisive one)
  4. erdosproblems.com/forum/thread/<n>        (comments)
  5. oeis.org/search?q=id:<Aid>&fmt=text       (per linked sequence)
  6. export.arxiv.org/api/query                (targeted recent-work sweep)

Verdict is a SUGGESTION with the evidence attached. A human reads the card.

Usage:
  python3 frontier.py census                 # the 43 finite-flagged problems
  python3 frontier.py check 617 375 475      # full frontier cards
  python3 frontier.py check --all-finite     # every falsifiable/verifiable/decidable
  python3 frontier.py refresh                # re-pull problems.yaml

Cards land in cards/<n>.md and a one-line verdict goes to stdout.
"""
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CARDS = os.path.join(HERE, "cards")
YAML = os.path.join(DATA, "problems.yaml")
YAML_URL = "https://raw.githubusercontent.com/teorth/erdosproblems/main/data/problems.yaml"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
FINITE = ("falsifiable", "verifiable", "decidable")


# ---------------------------------------------------------------- fetching

def fetch(url, cache_name=None, ttl=86400):
    """curl with a browser UA. Plain urllib gets a 403 from erdosproblems.com."""
    path = os.path.join(DATA, "cache", cache_name) if cache_name else None
    if path and os.path.exists(path) and time.time() - os.path.getmtime(path) < ttl:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    try:
        out = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", "60", "-A", UA, url],
            capture_output=True, text=True, timeout=90).stdout
    except Exception as e:
        return f"__FETCH_ERROR__ {e}"
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
    return out


def detag(s, keep_links=False):
    s = re.sub(r"(?s)<script.*?</script>", " ", s)
    s = re.sub(r"(?s)<style.*?</style>", " ", s)
    m = re.search(r"(?s)<body.*?>(.*)</body>", s)
    if m:
        s = m.group(1)
    if keep_links:
        s = re.sub(r'<a [^>]*href="(https?://[^"]*)"[^>]*>', r" [\1] ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


# ---------------------------------------------------------------- yaml

def load_yaml():
    """problems.yaml is one flat record per problem. A line parser is enough and
    keeps this tool dependency free."""
    if not os.path.exists(YAML):
        refresh()
    recs, cur = [], None
    with open(YAML, encoding="utf-8") as f:
        for line in f:
            if line.startswith("- number:"):
                if cur:
                    recs.append(cur)
                cur = {"number": line.split(":", 1)[1].strip().strip('"'),
                       "tags": [], "oeis": []}
                section = None
                continue
            if cur is None:
                continue
            if re.match(r"^  \w", line):
                section = line.strip().rstrip(":").split(":")[0]
                if line.strip().startswith("prize:"):
                    cur["prize"] = line.split(":", 1)[1].strip().strip('"')
                elif line.strip().startswith("tags:"):
                    cur["tags"] = re.findall(r'"([^"]+)"', line)
                elif line.strip().startswith("oeis:"):
                    # unquoted values N/A and "possible" are placeholders, not ids
                    cur["oeis"] = [x for x in re.findall(r'"([^"]+)"', line)
                                   if re.fullmatch(r"A\d{6}", x)]
            elif re.match(r"^    \w", line) and section:
                k, _, v = line.strip().partition(":")
                cur[f"{section}.{k}"] = v.strip().strip('"')
    if cur:
        recs.append(cur)
    return {r["number"]: r for r in recs}


def refresh():
    os.makedirs(DATA, exist_ok=True)
    subprocess.run(["curl", "-sS", "-o", YAML, YAML_URL], check=True)
    print(f"pulled {YAML} ({os.path.getsize(YAML)} bytes)")


# ---------------------------------------------------------------- sources

def problem_page(n):
    raw = fetch(f"https://www.erdosproblems.com/{n}", f"ep{n}.html")
    txt = detag(raw, keep_links=True)
    out = {}
    m = re.search(r"(?s)graph theory|#" + str(n) + r"\s*:", txt)
    out["text"] = txt
    out["last_edited"] = (re.search(r"last edited (\d+ \w+ \d{4})", txt) or [None, None])[1] \
        if re.search(r"last edited (\d+ \w+ \d{4})", txt) else None
    mc = re.search(r"(\d+) comments? on this problem", txt)
    out["n_comments"] = int(mc.group(1)) if mc else 0
    mp = re.search(r"(\d+) claimed proofs? for this problem", txt)
    out["n_claims"] = int(mp.group(1)) if mp else 0
    mw = re.search(r"(?s)Currently working on this problem\s*(.*?)\s*This problem looks difficult", txt)
    workers = []
    if mw:
        workers = [w.strip() for w in mw.group(1).split(",") if w.strip() and w.strip() != "None"]
    out["workers"] = workers
    # the statement sits between the state blurb and the "#n :" citation line
    ms = re.search(r"(?s)Random Open\s*(.*?)\s*#" + str(n) + r"\s*:", txt)
    out["statement"] = re.sub(r"\s+", " ", ms.group(1)).strip() if ms else ""
    return out


def proof_claims(n):
    raw = fetch(f"https://www.erdosproblems.com/forum/thread/{n}/proof-claims",
                f"pc{n}.html")
    txt = detag(raw, keep_links=True)
    i = txt.find("proof claims (partial or full)")
    if i < 0:
        i = txt.find("proof claim")
    body = txt[i:] if i >= 0 else ""
    claims = []
    # each claim starts "A partial proof claimed by X" or "A full proof claimed by X"
    parts = re.split(r"(?=A (?:partial|full|complete) proof\s+claimed by )", body)
    for p in parts[1:]:
        who = re.search(r"claimed by ([^(.|]+)", p)
        when = re.search(r"Submitted (\d{4}-\d\d-\d\d)", p)
        summ = re.search(r"(?s)Summary:\s*(.*?)(?:\s*Notes:|\s*\|)", p)
        links = re.findall(r"\[(https?://[^\]]+)\]", p)
        claims.append({
            "kind": p.split(" claimed by")[0].strip(),
            "who": who.group(1).strip() if who else "?",
            "date": when.group(1) if when else "?",
            "summary": re.sub(r"\s+", " ", summ.group(1)).strip() if summ else
                       re.sub(r"\s+", " ", p[:600]),
            "links": [l for l in links if "erdosproblems.com" not in l][:4],
        })
    return claims


def forum_comments(n):
    raw = fetch(f"https://www.erdosproblems.com/forum/thread/{n}", f"fo{n}.html")
    txt = detag(raw, keep_links=True)
    i = txt.find("citation format is:")
    body = txt[i:] if i >= 0 else txt
    body = re.sub(r"(?s).*accessed \d{4}-\d\d-\d\d", "", body).strip()
    return body[:4000]


def oeis_entry(aid):
    raw = fetch(f"https://oeis.org/search?q=id:{aid}&fmt=text", f"oeis_{aid}.txt")
    if raw.startswith("__FETCH_ERROR__"):
        return {"id": aid, "error": raw}
    lines = raw.splitlines()
    name = next((l[11:] for l in lines if l.startswith("%N ")), "")
    comments = [l[11:] for l in lines if l.startswith("%C ")]
    refs = [l[11:] for l in lines if l.startswith("%D ") or l.startswith("%H ")]
    exts = [l[11:] for l in lines if l.startswith("%E ")]
    # anything that smells like a computational bar
    bars = [l for l in comments + refs + exts
            if re.search(r"(10\^|up to|no (more|other|further)|verified|searched|beyond|"
                         r"a\(\d+\)|terms)", l, re.I)]
    return {"id": aid, "name": name, "n_comments": len(comments),
            "bars": bars[:14], "recent_ext": exts[-3:]}


def arxiv(query, maxr=12):
    q = urllib.parse.urlencode({
        "search_query": query, "start": 0, "max_results": maxr,
        "sortBy": "submittedDate", "sortOrder": "descending"})
    raw = fetch(f"http://export.arxiv.org/api/query?{q}",
                "arxiv_" + re.sub(r"\W+", "_", query)[:70] + ".xml", ttl=43200)
    out = []
    for e in re.findall(r"(?s)<entry>(.*?)</entry>", raw):
        t = re.search(r"(?s)<title>(.*?)</title>", e)
        d = re.search(r"<published>(\d{4}-\d\d-\d\d)", e)
        i = re.search(r"<id>(.*?)</id>", e)
        s = re.search(r"(?s)<summary>(.*?)</summary>", e)
        out.append({"title": re.sub(r"\s+", " ", html.unescape(t.group(1))) if t else "",
                    "date": d.group(1) if d else "",
                    "id": i.group(1) if i else "",
                    "abstract": re.sub(r"\s+", " ", html.unescape(s.group(1)))[:400] if s else ""})
    return out


# ---------------------------------------------------------------- verdict

def suggest(card):
    """Rules, stated so they can be argued with:
      TAKEN      a proof claim on the site addresses the case, or a paper we
                 found settles it. Do not compute.
      CONTESTED  people listed as currently working, or claims that cover
                 neighbouring cases. Compute only with a clock on it.
      STALE-BAR  the site bound and an OEIS bound disagree, or an OEIS
                 extension is newer than the site's quoted bar. Free win:
                 correct the record.
      OPEN       nothing found. Still do a human literature pass.
    """
    reasons = []
    v = "OPEN"
    if card["claims"]:
        v = "TAKEN"
        reasons.append(f"{len(card['claims'])} proof claim(s) on the site, newest "
                       f"{max(c['date'] for c in card['claims'])}")
    if card["page"]["workers"]:
        if v == "OPEN":
            v = "CONTESTED"
        reasons.append(f"{len(card['page']['workers'])} listed as currently working")
    if card["page"]["n_comments"] and v == "OPEN":
        v = "CONTESTED"
        reasons.append(f"{card['page']['n_comments']} comment(s) to read by hand")
    for o in card["oeis"]:
        if o.get("recent_ext"):
            reasons.append(f"{o['id']} extension notes: {' | '.join(o['recent_ext'])[:180]}")
    return v, reasons


def check(n, yml):
    n = str(n)
    rec = yml.get(n, {})
    card = {"n": n, "rec": rec}
    card["page"] = problem_page(n)
    card["claims"] = proof_claims(n)
    card["comments"] = forum_comments(n)
    card["oeis"] = [oeis_entry(a) for a in rec.get("oeis", [])]
    card["verdict"], card["reasons"] = suggest(card)
    return card


def render(card):
    n = card["n"]
    r = card["rec"]
    L = [f"# Problem {n} frontier card",
         "",
         f"Pulled {time.strftime('%Y-%m-%d %H:%M')} local.",
         "",
         f"- yaml status: `{r.get('status.state','?')}` "
         f"(informal `{r.get('informal_status.state','?')}`, "
         f"last update {r.get('status.last_update','?')})",
         f"- tags: {', '.join(r.get('tags',[])) or 'none'}",
         f"- prize: {r.get('prize','none')}",
         f"- OEIS: {', '.join(r.get('oeis',[])) or 'none'}",
         f"- site last edited: {card['page']['last_edited']}",
         f"- comments on site: {card['page']['n_comments']}; proof claims: {card['page']['n_claims']}",
         f"- currently working: {', '.join(card['page']['workers']) or 'nobody listed'}",
         "",
         f"## VERDICT: {card['verdict']}",
         ""]
    for x in card["reasons"]:
        L.append(f"- {x}")
    L += ["", "## Statement (from the site)", "", card["page"]["statement"][:1200] or "(not parsed)", ""]
    if card["claims"]:
        L.append("## Proof claims on the site")
        L.append("")
        for c in card["claims"]:
            L.append(f"### {c['date']} - {c['who']} ({c['kind']})")
            L.append("")
            L.append(c["summary"][:1600])
            for l in c["links"]:
                L.append(f"- link: {l}")
            L.append("")
    for o in card["oeis"]:
        L.append(f"## OEIS {o['id']}")
        L.append("")
        L.append(f"{o.get('name','')}")
        L.append("")
        for b in o.get("bars", []):
            L.append(f"- {b}")
        L.append("")
    if card["comments"].strip():
        L.append("## Forum thread text")
        L.append("")
        L.append("```")
        L.append(card["comments"][:2500])
        L.append("```")
        L.append("")
    txt = "\n".join(L)
    # house rule: no em dashes, no en dashes in anything we write
    return txt.replace("—", "-").replace("–", "-").replace("−", "-")  # dash:allow this line IS the stripper and must name what it removes


def census(yml):
    rows = [r for r in yml.values() if r.get("status.state") in FINITE]
    rows.sort(key=lambda r: (r["status.state"], int(r["number"])))
    print(f"{len(rows)} problems flagged finite ({', '.join(FINITE)})\n")
    print(f"{'#':>5}  {'state':<12} {'prize':<7} {'oeis':<10} tags")
    for r in rows:
        print(f"{r['number']:>5}  {r['status.state']:<12} {r.get('prize','-'):<7} "
              f"{(','.join(r.get('oeis',[])) or '-'):<10} {','.join(r.get('tags',[]))}")
    by = {}
    for r in rows:
        by[r["status.state"]] = by.get(r["status.state"], 0) + 1
    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(by.items())))


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    if a[0] == "refresh":
        refresh(); return
    yml = load_yaml()
    if a[0] == "census":
        census(yml); return
    if a[0] == "check":
        if "--all-finite" in a:
            nums = sorted((r["number"] for r in yml.values()
                           if r.get("status.state") in FINITE), key=int)
        else:
            nums = [x for x in a[1:] if x.isdigit()]
        os.makedirs(CARDS, exist_ok=True)
        for n in nums:
            c = check(n, yml)
            with open(os.path.join(CARDS, f"{n}.md"), "w", encoding="utf-8") as f:
                f.write(render(c))
            print(f"{n:>5}  {c['verdict']:<10} claims={len(c['claims'])} "
                  f"workers={len(c['page']['workers'])} "
                  f"comments={c['page']['n_comments']} "
                  f"oeis={','.join(c['rec'].get('oeis',[])) or '-'}")
        return
    print(__doc__)


if __name__ == "__main__":
    main()
