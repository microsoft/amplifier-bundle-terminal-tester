import sys, json, hashlib, re
from pathlib import Path
import yaml

repo = Path(sys.argv[1])
out = {}
for p in sorted((repo/"agents").glob("*.md")):
    raw = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
    fm_text = m.group(1)
    body = raw[m.end():]
    fm = yaml.safe_load(fm_text)
    desc = fm["meta"]["description"]
    out[p.name] = {
        "desc_chars": len(desc),
        "desc_md5": hashlib.md5(desc.encode()).hexdigest(),
        "example_count": desc.count("<example>"),
        "commentary_count": desc.count("<commentary>"),
        "body_md5": hashlib.md5(body.encode()).hexdigest(),
        "body_bytes": len(body.encode()),
        "has_tools": "tools" in fm,
        "model_role": fm.get("model_role"),
        "file_bytes": len(raw.encode()),
    }
out["_total_desc_chars"] = sum(v["desc_chars"] for k,v in out.items() if not k.startswith("_"))
print(json.dumps(out, indent=2))
