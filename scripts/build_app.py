#!/usr/bin/env python3
"""Injecte data/omashing.json dans app/template.html.

    python3 scripts/build_app.py            # -> index.html (page complète, PWA)
    python3 scripts/build_app.py --fragment out.html   # -> fragment sans <head>

Le gabarit `app/template.html` contient le <title>, les <link> de polices, le
<style>, puis le balisage et le script. Pour `index.html` on le coupe après
</style> : la première moitié va dans <head>, la seconde dans <body>.
"""
import argparse, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEAD = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Les 348 accords colorimétriques de Sanzo Wada, pour composer une tenue, une slide, ou autre chose.">
<meta name="theme-color" content="#E6E6E3" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121315" media="(prefers-color-scheme: dark)">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icons/icon-192.png" sizes="192x192" type="image/png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Omashing">
"""
TAIL = """
<script>
if ('serviceWorker' in navigator)
  addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
</script>
</body>
</html>
"""

ap = argparse.ArgumentParser()
ap.add_argument('--fragment', metavar='PATH',
                help="écrit un fragment sans squelette HTML (pour un hôte qui l'ajoute)")
args = ap.parse_args()

data = json.loads((ROOT / 'data' / 'omashing.json').read_text(encoding='utf-8'))
tpl = (ROOT / 'app' / 'template.html').read_text(encoding='utf-8')
token = '/*OMASHING_DATA*/null'
if token not in tpl:
    raise SystemExit('marqueur de données introuvable dans app/template.html')
page = tpl.replace(token, json.dumps(data, ensure_ascii=False, separators=(',', ':')))

if args.fragment:
    out = pathlib.Path(args.fragment)
    out.write_text(page, encoding='utf-8')
else:
    split = page.index('</style>') + len('</style>')
    out = ROOT / 'index.html'
    out.write_text(HEAD + page[:split] + '\n</head>\n<body>\n' + page[split:] + TAIL,
                   encoding='utf-8')
print(f"{out} — {len(out.read_bytes()):,} octets")
