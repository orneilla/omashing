#!/usr/bin/env python3
"""Injecte data/omashing.json dans app/template.html et écrit index.html.

    python3 scripts/build_app.py
"""
import json, pathlib

root = pathlib.Path(__file__).resolve().parent.parent
data = json.loads((root / 'data' / 'omashing.json').read_text(encoding='utf-8'))
tpl = (root / 'app' / 'template.html').read_text(encoding='utf-8')
token = '/*OMASHING_DATA*/null'
if token not in tpl:
    raise SystemExit('marqueur de données introuvable dans app/template.html')
out = tpl.replace(token, json.dumps(data, ensure_ascii=False, separators=(',', ':')))
(root / 'index.html').write_text(out, encoding='utf-8')
print(f"index.html écrit — {len(out.encode()):,} octets")
