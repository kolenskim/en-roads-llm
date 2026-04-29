
Purpose: Print enroads_core.py

"""En-ROADS Climate Scenario Tool - Single file for Google Colab."""
import re, os, json, sys

# === URL Builder ===
ENROADS_URL = "https://en-roads.climateinteractive.org/scenario.html"
def build_url(params, v="26.4.0"):
    parts = [f"v={v}"]
    for pid, val in sorted(params.items()):
        parts.append(f"{pid}={int(val)}" if isinstance(val, float) and val == int(val) else f"{pid}={val}")
    return f"{ENROADS_URL}?{'&'.join(parts)}"

# === Scenario Actions (20 main policy levers) ===
_A = [
    ("Coal", ["coal","coal tax","discourage coal"], "p516", -30, -50, 200,
     {"highly encouraged":-50,"status quo":-30,"discouraged":30,"highly discouraged":100,"max tax":200}),
    ("Oil", ["oil","oil tax","petroleum","discourage oil"], "p517", 15, -50, 200,
     {"highly encouraged":-25,"status quo":15,"discouraged":50,"highly discouraged":100,"max tax":200}),
    ("Natural Gas", ["natural gas","gas","gas tax","discourage gas"], "p518", -30, -50, 200,
     {"highly encouraged":-50,"status quo":-30,"discouraged":30,"highly discouraged":100,"max tax":200}),
    ("Renewables", ["renewables","renewable","solar","wind","clean energy","subsidize renewables"], "p520", -25, -100, 50,
     {"highly encouraged":-80,"encouraged":-50,"status quo":-25,"discouraged":10,"highly discouraged":50}),
    ("Bioenergy", ["bioenergy","biomass","biofuel"], "p519", -15, -50, 200,
     {"highly encouraged":-40,"status quo":-15,"discouraged":30,"highly discouraged":100}),
    ("Nuclear", ["nuclear","nuclear energy","nuclear power","atomic"], "p521", -30, -100, 50,
     {"highly encouraged":-80,"encouraged":-50,"status quo":-30,"discouraged":10,"highly discouraged":50}),
    ("New Zero-Carbon Tech", ["new tech","breakthrough","hydrogen","fusion"], "p35", 0, 0, 2,
     {"status quo":0,"breakthrough":1,"huge breakthrough":2}),
    ("Carbon Price", ["carbon price","carbon tax","carbon pricing","co2 tax","emissions tax"], "p39", 5, 0, 250,
     {"status quo":5,"low":15,"medium":40,"high":80,"very high":150,"maximum":250}),
    ("Buildings Efficiency", ["building efficiency","industry efficiency","buildings and industry"], "p47", 1.2, 0, 3,
     {"discouraged":0.5,"status quo":1.2,"increased":2.0,"highly increased":3.0}),
    ("Transport Efficiency", ["transport efficiency","vehicle efficiency","fuel efficiency"], "p50", 0.5, 0, 3,
     {"status quo":0.5,"increased":1.5,"highly increased":3.0}),
    ("Transport Electrification", ["ev","electric vehicle","electric cars","ev subsidies","electrify transport"], "p373", 7, 0, 50,
     {"status quo":7,"encouraged":15,"highly encouraged":35,"maximum":50}),
    ("Buildings Electrification", ["building electrification","heat pump","electric heating","electrify buildings"], "p375", 0, 0, 50,
     {"status quo":0,"encouraged":10,"highly encouraged":35,"maximum":50}),
    ("Population", ["population","population growth","birth rate"], "p63", 10.2, 9.0, 11.4,
     {"lowest":9.0,"low":9.5,"status quo":10.2,"high":10.8,"highest":11.4}),
    ("Economic Growth", ["economic growth","gdp","economy"], "p235", 1.5, 0.5, 2.5,
     {"low":0.8,"status quo":1.5,"high":2.2}),
    ("Agriculture Methane", ["methane","agriculture emissions","livestock","food","diet","meat"], "p60", 0, 0, 100,
     {"status quo":0,"reduced":30,"highly reduced":75,"maximum":100}),
    ("Waste Emissions", ["waste","leakage","landfill","waste emissions"], "p61", 0, 0, 100,
     {"status quo":0,"reduced":30,"highly reduced":75,"maximum":100}),
    ("Deforestation", ["deforestation","forest","forests","logging","stop deforestation"], "p57", 0, -10, 1,
     {"highly reduced":-6,"reduced":-2,"status quo":0,"increased":0.5}),
    ("Nature-Based Removal", ["afforestation","reforestation","plant trees","natural carbon removal","soil carbon"], "p417", 0, 0, 100,
     {"status quo":0,"low":20,"medium":50,"high":80,"maximum":100}),
    ("Tech Carbon Removal", ["dac","direct air capture","carbon capture","ccs","tech removal","beccs"], "p67", 0, 0, 100,
     {"status quo":0,"low":20,"medium":50,"high":80,"maximum":100}),
]

ACTIONS = [{"name":a[0],"aliases":a[1],"param":a[2],"default":a[3],"min":a[4],"max":a[5],"levels":a[6]} for a in _A]

def find_action(text):
    t = text.lower()
    words = set(re.split(r'\W+', t))
    best, best_s = None, 0
    for a in ACTIONS:
        for al in a["aliases"]:
            if al in t:
                s = len(al)*2
                if s > best_s: best_s, best = s, a
                continue
            if set(al.split()).issubset(words):
                s = len(al)
                if s > best_s: best_s, best = s, a
    return best

def resolve_level(action, text):
    t = text.lower()
    best_l, best_s = None, 0
    for ln, lv in action["levels"].items():
        if ln in t and len(ln) > best_s: best_s, best_l = len(ln), lv
    if best_l is not None: return best_l
    d, mn, mx = action["default"], action["min"], action["max"]
    p = action["param"]
    is_enc = any(w in t for w in ["subsidize","encourage","invest","promote","boost"])
    is_dis = any(w in t for w in ["tax","discourage","ban","phase out","eliminate","reduce","stop","restrict"])
    clean = p in ("p520","p521","p519")
    fossil = p in ("p516","p517","p518")
    if is_enc: te = mn
    elif is_dis: te = mx
    elif clean: te = mn
    elif fossil: te = mx
    else: te = mx
    if p in ("p57","p63"):
        te = mn if (is_dis or any(w in t for w in ["reduce","stop","less","lower","slow"])) else mx
    if p in ("p47","p50","p373","p375","p60","p61","p417","p67","p39"): te = mx
    if any(w in t for w in ["maximum","max","full","ban","eliminate","phase out"]): return te
    if any(w in t for w in ["very high","aggressive","heavily"]): return d+0.75*(te-d)
    if any(w in t for w in ["high","strong","significant","major"]): return d+0.5*(te-d)
    if any(w in t for w in ["moderate","medium","some"]): return d+0.3*(te-d)
    if any(w in t for w in ["slight","small","minor","low"]): return d+0.15*(te-d)
    m = re.search(r'(-?\d+\.?\d*)', text)
    if m: return max(mn, min(mx, float(m.group(1))))
    return d+0.3*(te-d)

# === Parser ===
def parse_scenario(text):
    parts = re.split(r'[;.\n]', text)
    frags = []
    for part in parts:
        sub = re.split(r',\s*(?:and\s+)?|\s+and\s+', part)
        if len(sub) > 1 and sum(1 for s in sub if s.strip() and find_action(s.strip())) >= 2:
            frags.extend(sub)
        else:
            frags.append(part)
    results, seen = [], set()
    for f in frags:
        f = f.strip()
        if not f or len(f) < 3: continue
        a = find_action(f)
        if a and a["param"] not in seen:
            v = resolve_level(a, f)
            rng = a["max"] - a["min"]
            step = 0.1 if rng <= 5 else 1
            v = round(v) if step >= 1 else round(round(v/step)*step, 2)
            v = max(a["min"], min(a["max"], v))
            results.append({**{k: a[k] for k in ("param","name","description","default","min","max") if k in a}, "value": v})
            seen.add(a["param"])
    return results

# === Presets ===
PRESETS = {
    "baseline": {},
    "net zero 2050": {"p516":100,"p517":80,"p518":60,"p520":-80,"p521":-60,"p39":100,"p47":2.5,"p50":2.5,"p373":30,"p375":25,"p57":-5,"p60":60,"p61":60,"p417":60,"p67":50},
    "maximum action": {"p516":200,"p517":200,"p518":200,"p520":-100,"p521":-100,"p35":2,"p39":250,"p47":3,"p50":3,"p373":50,"p375":50,"p63":9.0,"p235":0.5,"p60":100,"p61":100,"p57":-10,"p417":100,"p67":100},
    "renewable revolution": {"p516":80,"p517":50,"p518":50,"p520":-90,"p39":60,"p373":40,"p375":30},
}

# === Web Search ===
def web_search(query, max_results=5):
    import requests
    try:
        r = requests.get("https://search.brave.com/search", params={"q":query,"source":"web"},
                         headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}, timeout=15)
        if r.status_code != 200: return []
        html = r.text
        positions = list(re.finditer(r'data-pos="(\d+)"[^>]*data-type="web"', html))
        results = []
        for i, m in enumerate(positions[:max_results]):
            start = max(0, m.start()-200)
            end = positions[i+1].start() if i+1 < len(positions) else start+5000
            block = html[start:end]
            url_m = re.search(r'href="(https?://(?!search\.brave)[^"]+)"', block)
            title_m = re.search(r'snippet-title[^>]*>(.*?)</span>', block, re.DOTALL)
            desc_m = re.search(r'class="content[^"]*line-clamp[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL)
            url = url_m.group(1) if url_m else ""
            title = re.sub(r'<[^>]+>','',title_m.group(1)).strip() if title_m else url
            desc = re.sub(r'<[^>]+>','',desc_m.group(1)).strip() if desc_m else ""
            if url: results.append({"title":title,"snippet":desc,"url":url})
        return results
    except: return []

def fetch_page(url, max_chars=3000):
    import requests
    if not url.startswith("http"): url = "https://"+url
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        if "pdf" in r.headers.get("content-type","") or url.endswith(".pdf"): return "[PDF]"
        html = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>","",r.text,flags=re.DOTALL|re.IGNORECASE)
        html = re.sub(r"<(p|div|br|h[1-6]|li|tr)[^>]*>","\n",html,flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>"," ",html).replace("&amp;","&").replace("&lt;","<").replace("&gt;",">").replace("&nbsp;"," ")
        return re.sub(r"\n\s*\n+","\n\n",re.sub(r"[ \t]+"," ",text)).strip()[:max_chars]
    except Exception as e: return f"Error: {e}"

# === Agent ===
TOOLS = [
    {"type":"function","function":{"name":"web_search","description":"Search the web for current climate/energy/policy information.",
     "parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type":"function","function":{"name":"read_webpage","description":"Fetch text content of a web page URL.",
     "parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},
    {"type":"function","function":{"name":"build_scenario","description":"Build En-ROADS scenario. Params: "+", ".join(f'{a["param"]}={a["name"]}({a["min"]}-{a["max"]})' for a in ACTIONS),
     "parameters":{"type":"object","properties":{"params":{"type":"object","additionalProperties":{"type":"number"}},"name":{"type":"string"}},"required":["params"]}}},
    {"type":"function","function":{"name":"parse_scenario","description":"Parse natural language climate policies into En-ROADS parameters.",
     "parameters":{"type":"object","properties":{"description":{"type":"string"}},"required":["description"]}}},
]

SYSTEM_PROMPT = """You are an expert climate policy advisor with the MIT En-ROADS simulator.
You can search the web for current climate news, then build En-ROADS scenarios.
Parameters: """ + ", ".join(f'{a["param"]}:{a["name"]}({a["min"]}-{a["max"]},default={a["default"]})' for a in ACTIONS) + """
For energy sources, negative=subsidized, positive=taxed. Always provide the En-ROADS URL."""

def execute_tool(name, args):
    if name == "web_search":
        results = web_search(args["query"])
        return "\n".join(f"{i+1}. **{r['title']}**\n   {r['snippet']}\n   {r['url']}" for i,r in enumerate(results)) or "No results."
    elif name == "read_webpage": return fetch_page(args["url"])
    elif name == "build_scenario":
        params = {k:float(v) for k,v in args["params"].items()}
        url = build_url(params)
        lines = [f"**{args.get('name','Scenario')}**\n"]
        for a in ACTIONS:
            if a["param"] in params:
                v = params[a["param"]]
                lines.append(f"  {a['name']}: {a['default']} → {v} {'↑' if v>a['default'] else '↓' if v<a['default'] else '='}")
        lines.append(f"\n🔗 {url}")
        return "\n".join(lines)
    elif name == "parse_scenario":
        changes = parse_scenario(args["description"])
        if not changes: return "No actions recognized."
        params = {c["param"]:c["value"] for c in changes}
        return "\n".join(f"  {c['name']}: {c.get('default','?')} → {c['value']}" for c in changes) + f"\n\n🔗 {build_url(params)}"
    return "Unknown tool"

def agent_chat(client, messages):
    from openai import OpenAI
    model = os.environ.get("ENROADS_MODEL", "gpt-4o-mini")
    while True:
        resp = client.chat.completions.create(model=model, messages=messages, tools=TOOLS, temperature=0.7)
        msg = resp.choices[0].message
        if not msg.tool_calls: return msg.content or ""
        messages.append(msg)
        for tc in msg.tool_calls:
            fn = tc.function.name
            try: fa = json.loads(tc.function.arguments)
            except: fa = {}
            print(f"  🔧 {fn}({', '.join(f'{k}={str(v)[:50]}' for k,v in fa.items())})", file=sys.stderr)
            messages.append({"role":"tool","tool_call_id":tc.id,"content":execute_tool(fn, fa)})

print("✅ En-ROADS tool loaded! Use parse_scenario() and build_url(), or agent_chat() with an LLM.")