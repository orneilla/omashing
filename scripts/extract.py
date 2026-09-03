#!/usr/bin/env python3
"""Extrait les 159 couleurs et les 348 accords du manuel vers data/omashing.json.

Prérequis : pymupdf, numpy, et le PDF du manuel à la racine du dépôt.

    pip install pymupdf numpy
    python3 scripts/extract.py

Pipeline
--------
1. `scripts/colors.tsv` : l'index des 159 couleurs (n°, nom japonais, kana, nom
   anglais, CMJN), relevé sur les planches d'index (p. 284-350 du PDF). 154 des
   159 valeurs CMJN sont re-confirmées automatiquement par l'OCR (étape 0).
2. Les planches d'accords sont repérées géométriquement :
     p.  27- 86 : 2 accords/page, 2 couleurs (bandes côte à côte)
     p.  89-148 : 2 accords/page, 3 couleurs
     p. 151-258 : 1 accord/page, 4 couleurs (disposition en croix)
   La couleur de chaque pastille est échantillonnée au centre (médiane).
3. Les noms anglais imprimés sous les pastilles sont lus dans la couche texte du
   PDF et appariés au catalogue par similarité (difflib).
4. Nom + couleur décident ensemble : le nom imprimé prime quand il est complet et
   sans ambiguïté ; la couleur tranche les noms tronqués par l'OCR et les doublons
   (Eugenia Red et Grayish Lavender figurent deux fois au catalogue).
5. L'index inverse du livre (p. 261-282 : couleur -> liste d'accords) sert de
   contrôle indépendant et corrige les cas restants.
6. Le hex publié est mesuré sur le scan (planches + index), normalisé par le blanc
   du papier de chaque page ; le CMJN d'origine est conservé tel quel.
"""
import difflib, glob, json, os, re, sys
import numpy as np
import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pdfs = glob.glob(os.path.join(ROOT, '*.pdf'))
if not pdfs:
    sys.exit("PDF du manuel introuvable à la racine du dépôt.")
D = pymupdf.open(pdfs[0])
DPI, SCALE = 100, 100 / 72.0

COLORS = []
with open(os.path.join(ROOT, 'scripts', 'colors.tsv'), encoding='utf-8') as fh:
    for line in fh:
        p = line.rstrip('\n').split('\t')
        COLORS.append(dict(id=int(p[0]), jp=p[1], kana=p[2], en=p[3],
                           cmyk=[int(x) for x in p[4:8]]))
N = len(COLORS)
assert N == 159, N

def norm(s):
    s = s.lower().replace('’', "'").replace('/', ' ')
    return ' '.join(re.sub(r"[^a-z' ]", ' ', s).split())
ENN = [norm(c['en']) for c in COLORS]

SECTIONS = [(range(27, 87), 2, 2), (range(89, 149), 2, 3), (range(151, 259), 1, 4)]
CMYK_RE = re.compile(r'C\s*\.?\s*([\dOolI]{1,3})\s*\.?\s*M\s*\.?\s*([\dOolI]{1,3})'
                     r'\s*\.?\s*Y\s*\.?\s*([\dOolI]{1,3})\s*\.?\s*[Kk]\s*\.?\s*([\dOolI]{1,3})')
digits = lambda s: int(s.replace('O', '0').replace('o', '0').replace('l', '1').replace('I', '1'))


# ---------------------------------------------------------------- 0. contrôle CMJN
def check_cmyk():
    seen = set()
    for pg in range(284, 352):
        for m in CMYK_RE.finditer(' '.join(D[pg].get_text().split())):
            seen.add(tuple(digits(x) for x in m.groups()))
    ok = sum(1 for c in COLORS if tuple(c['cmyk']) in seen)
    print(f"  CMJN re-confirmés par l'OCR de l'index : {ok}/{N}")


# ---------------------------------------------------------------- 1. pastilles
def page_rgb(pno):
    px = D[pno].get_pixmap(dpi=DPI)
    return np.frombuffer(px.samples, np.uint8) \
             .reshape(px.height, px.width, px.n)[:, :, :3].astype(float)

def ink_mask(a):
    mx, mn = a.max(2), a.min(2)
    return ((mx - mn) > 20) | ((255 - mx) > 50)

def runs(profile, thr, minlen):
    out, start = [], None
    for i, v in enumerate(profile):
        if v > thr and start is None:
            start = i
        elif v <= thr and start is not None:
            if i - start >= minlen:
                out.append((start, i))
            start = None
    if start is not None and len(profile) - start >= minlen:
        out.append((start, len(profile)))
    return out

def median_at(a, cx, cy, r=4):
    return np.median(a[int(cy - r):int(cy + r) + 1,
                       int(cx - r):int(cx + r) + 1].reshape(-1, 3), axis=0)

def widest_run(row):
    xs = np.nonzero(row)[0]
    if not len(xs):
        return (0, 0)
    best, s, prev = (0, 0), xs[0], xs[0]
    for x in xs[1:]:
        if x - prev > 3:
            if prev - s > best[1] - best[0]:
                best = (s, prev)
            s = x
        prev = x
    return (s, prev) if prev - s > best[1] - best[0] else best

def strip_bands(pno):
    """Bandes horizontales des planches à 2 et 3 couleurs."""
    a = page_rgb(pno)
    m = ink_mask(a)
    out = []
    for y0, y1 in runs(m.mean(1), 0.30, 15):
        rs = runs(m[y0:y1].mean(0), 0.55, 15)
        if rs:
            out.append((rs[0][0], y0, rs[-1][1], y1))
    return a, out

def strip_colors(a, box, n):
    x0, y0, x1, y1 = box
    w, cy = (x1 - x0) / n, (y0 + y1) / 2
    return [median_at(a, x0 + w * (i + .5), cy) for i in range(n)]

def cross_colors(pno):
    """Planche à 4 couleurs : renvoie [haut, gauche, droite, bas]."""
    a = page_rgb(pno)
    m = ink_mask(a)
    reg = runs(m.mean(1), 0.30, 15)
    if not reg:
        return a, None
    y0, y1 = reg[0][0], reg[-1][1]
    W = [widest_run(m[y]) for y in range(y0, y1)]
    ext = np.array([b - a_ for a_, b in W])
    band = np.nonzero(ext > 0.90 * ext.max())[0]
    b0, b1 = band[0], band[-1]
    bx0 = int(np.median([W[i][0] for i in band]))
    bx1 = int(np.median([W[i][1] for i in band]))
    above = [i for i in range(b0) if ext[i] > 20]
    below = [i for i in range(b1 + 1, len(ext)) if ext[i] > 20]
    if not (above or below):
        return a, None
    cx0 = int(np.median([W[i][0] for i in above + below]))
    cx1 = int(np.median([W[i][1] for i in above + below]))
    cxm, bym = (cx0 + cx1) / 2, y0 + (b0 + b1) / 2
    return a, [median_at(a, cxm, y0 + (above[0] + above[-1]) / 2) if above else None,
               median_at(a, (bx0 + cx0) / 2, bym),
               median_at(a, (bx1 + cx1) / 2, bym),
               median_at(a, cxm, y0 + (below[0] + below[-1]) / 2) if below else None]


# ---------------------------------------------------------------- 2. noms imprimés
def name_candidates(pno):
    raw = []
    for blk in D[pno].get_text('dict')['blocks']:
        if blk['type'] != 0:
            continue
        for ln in blk['lines']:
            t = ''.join(s['text'] for s in ln['spans']).strip()
            if t:
                raw.append((ln['bbox'], t))
    merged = list(raw)                       # recolle les noms coupés en deux
    for ba, ta in raw:
        for bb, tb in raw:
            if ba is bb:
                continue
            if abs(ba[1] - bb[1]) < 4 and 0 < bb[0] - ba[2] < 25:
                merged.append(((ba[0], min(ba[1], bb[1]), bb[2], max(ba[3], bb[3])),
                               ta + ' ' + tb))
    items = []
    for bb, t in merged:
        c = norm(t)
        if len(c) < 3:
            continue
        sc = np.array([difflib.SequenceMatcher(None, c, e).ratio() for e in ENN])
        if sc.max() >= 0.66:
            items.append(dict(x=(bb[0] + bb[2]) / 2, y=(bb[1] + bb[3]) / 2, sc=sc, raw=t))
    return items

def rows_of(items, tol=6):
    items = sorted(items, key=lambda i: i['y'])
    rows, cur = [], []
    for it in items:
        if cur and it['y'] - cur[-1]['y'] > tol:
            rows.append(sorted(cur, key=lambda i: i['x']))
            cur = []
        cur.append(it)
    if cur:
        rows.append(sorted(cur, key=lambda i: i['x']))
    return rows

def slots_for_page(pno, per, ncol):
    items = name_candidates(pno)
    if ncol == 4:
        a, cols = cross_colors(pno)
        if not cols:
            return None
        rs = [r for r in rows_of(items) if r]
        order = []
        if len(rs) == 3 and [len(r) for r in rs] == [1, 2, 1]:
            order = [rs[0][0], rs[1][0], rs[1][1], rs[2][0]]
        return [[dict(rgb=cols[k],
                      t=order[k]['sc'] if order else None,
                      raw=order[k]['raw'] if order else None) for k in range(4)]]
    a, boxes = strip_bands(pno)
    if len(boxes) != per:
        return None
    out = []
    for box in boxes:
        x0, y0, x1, y1 = box
        cols = strip_colors(a, box, ncol)
        near_band = [it for it in items if y1 / SCALE < it['y'] < y1 / SCALE + 60]
        slot = []
        for k in range(ncol):
            cx = (x0 + (x1 - x0) * (k + .5) / ncol) / SCALE
            near = sorted((it for it in near_band
                           if abs(it['x'] - cx) < (x1 - x0) / ncol / SCALE * .55),
                          key=lambda it: -it['sc'].max())
            slot.append(dict(rgb=cols[k],
                             t=near[0]['sc'] if near else None,
                             raw=near[0]['raw'] if near else None))
        out.append(slot)
    return out


# ---------------------------------------------------------------- 3. attribution
def collect_plates():
    plates = []
    for rng, per, ncol in SECTIONS:
        for pno in rng:
            s = slots_for_page(pno, per, ncol)
            if s is None:
                sys.exit(f"planche illisible p.{pno}")
            for combo in s:
                plates.append(dict(page=pno, ncol=ncol, slots=combo))
    for i, pl in enumerate(plates, 1):
        pl['id'] = i
    assert len(plates) == 348, len(plates)
    return plates

def scan_model(plates):
    """Couleur moyenne de chaque teinte telle qu'elle sort du scan."""
    from numpy.linalg import lstsq
    samples = [[] for _ in range(N)]
    for pl in plates:
        for s in pl['slots']:
            if s['t'] is None:
                continue
            i = int(s['t'].argmax())
            if s['t'][i] > 0.90 and s['t'][i] - np.sort(s['t'])[-2] > 0.08:
                samples[i].append(s['rgb'])
    have = [i for i in range(N) if len(samples[i]) >= 3]
    pal = np.array([[255 * (1 - v / 100) * (1 - c['cmyk'][3] / 100)
                     for v in c['cmyk'][:3]] for c in COLORS])
    A = np.hstack([pal[have], np.ones((len(have), 1))])
    Y = np.array([np.mean(samples[i], 0) for i in have])
    W = lstsq(A, Y, rcond=None)[0]
    emp = np.hstack([pal, np.ones((N, 1))]) @ W       # repli pour les teintes rares
    for i in have:
        emp[i] = np.mean(samples[i], 0)
    sig = np.maximum(np.array([np.std(samples[i], 0) for i in have]).mean(0), 6.0)
    print(f"  teintes calibrées sur les planches : {len(have)}/{N}")
    return emp, sig, samples

def assign(plates, emp, sig):
    dist = lambda rgb: np.sqrt((((np.array(rgb) - emp) / sig) ** 2).sum(1))
    for pl in plates:
        picks = []
        for s in pl['slots']:
            raw, t = s['raw'], s['t']
            nr = norm(raw) if raw else ''
            if t is None or len(nr) < 4 or t.max() < 0.72:
                cand = list(range(N))                      # nom illisible -> couleur
            else:                                          # nom complet, ou tronqué
                cand = sorted({i for i in range(N) if t[i] >= 0.90} |
                              {i for i in range(N) if nr in ENN[i]}) or [int(t.argmax())]
            d = dist(s['rgb'])
            cand.sort(key=lambda i: d[i])
            picks.append(dict(i=cand[0], rgb=[float(v) for v in s['rgb']], d=float(d[cand[0]])))
        pl['picks'] = picks
    return plates


# ---------------------------------------------------------------- 4. index inverse
def reverse_index():
    """p. 261-282 : couleur -> numéros d'accords. Contrôle indépendant."""
    three = re.compile(r'^[\dOolI]{3}$')
    anchors, numbers = [], []
    for pg in range(261, 283):
        lines = []
        for blk in D[pg].get_text('dict')['blocks']:
            if blk['type'] != 0:
                continue
            for ln in blk['lines']:
                t = ''.join(s['text'] for s in ln['spans']).strip()
                if t:
                    lines.append((ln['bbox'], t))
        cand = []
        for bb, t in lines:
            if bb[0] <= 120:
                if CMYK_RE.search(t):
                    cand.append((bb[1], 'cmyk', t))
                else:
                    n = norm(t)
                    if len(n) >= 4 and max(difflib.SequenceMatcher(None, n, e).ratio()
                                           for e in ENN) >= 0.80:
                        cand.append((bb[1], 'name', t))
            else:
                for tok in t.split():
                    if three.match(tok) and 1 <= digits(tok) <= 348:
                        numbers.append((pg, bb[1], digits(tok)))
        cand.sort()
        keep = []
        for y, kind, t in cand:
            if not (keep and y - keep[-1][0] < 18):
                keep.append((y, kind, t))
        anchors += [(pg, y, kind, t) for y, kind, t in keep]

    # alignement monotone ancres -> couleurs (certaines entrées échappent à l'OCR)
    sim = lambda ai, ci: (0.45 if anchors[ai][2] != 'name' else
                          difflib.SequenceMatcher(None, norm(anchors[ai][3]), ENN[ci]).ratio())
    NA = len(anchors)
    dp = np.full((NA + 1, N + 1), -1e9)
    dp[0, 0] = 0
    back = {}
    for i in range(NA + 1):
        for j in range(N + 1):
            if dp[i, j] == -1e9:
                continue
            if j < N and dp[i, j] - .6 > dp[i, j + 1]:
                dp[i, j + 1] = dp[i, j] - .6
                back[(i, j + 1)] = (i, j, None)
            if i < NA and j < N and dp[i, j] + sim(i, j) > dp[i + 1, j + 1]:
                dp[i + 1, j + 1] = dp[i, j] + sim(i, j)
                back[(i + 1, j + 1)] = (i, j, 'm')
    pos, pairs = (NA, N), []
    while pos != (0, 0):
        i, j, kind = back[pos]
        if kind == 'm':
            pairs.append((i, j))
        pos = (i, j)
    a2c = dict(pairs)

    by_page = {}
    for ai, (pg, y, _, _) in enumerate(anchors):
        if ai in a2c:
            by_page.setdefault(pg, []).append((y, a2c[ai]))
    book = {i: set() for i in range(N)}
    for pg, y, v in numbers:                 # les numéros sont lus juste au-dessus
        near = [(ny - y, ci) for ny, ci in by_page.get(pg, []) if 3 <= ny - y <= 30]
        if near:
            book[min(near)[1]].add(v)
    print(f"  index inverse : {sum(1 for v in book.values() if v)} couleurs relues")
    return book

def apply_book(plates, book, emp, sig):
    by_combo = {pl['id']: pl for pl in plates}
    mine = {i: set() for i in range(N)}
    for pl in plates:
        for p in pl['picks']:
            mine[p['i']].add(pl['id'])
    d_to = lambda rgb, i: float(np.sqrt((((np.array(rgb) - emp[i]) / sig) ** 2).sum()))
    fixed = skipped = 0
    for i, combos in book.items():
        for cid in sorted(combos - mine[i]):
            pl = by_combo[cid]
            opts = [(d_to(p['rgb'], i) - p['d'], d_to(p['rgb'], i), k)
                    for k, p in enumerate(pl['picks'])
                    if not (p['i'] in book and cid in book[p['i']])]
            if not opts:
                skipped += 1
                continue
            delta, dist, k = min(opts)
            if dist > 9:                     # numéro probablement mal océrisé
                skipped += 1
                continue
            pl['picks'][k]['i'] = i
            mine[i].add(cid)
            fixed += 1
    print(f"  corrections issues de l'index inverse : {fixed} (écartées : {skipped})")
    return plates


# ---------------------------------------------------------------- 5. couleurs mesurées
INDEX_PAGES = [(284, 4), (286, 5), (288, 5), (290, 5), (292, 5), (294, 5), (296, 5),
               (298, 4), (300, 4), (302, 5), (304, 5), (306, 5), (308, 5), (310, 5),
               (312, 5), (314, 5), (316, 5), (318, 5), (320, 4), (322, 5), (324, 5),
               (326, 5), (328, 4), (330, 4), (332, 5), (334, 5), (336, 5), (338, 4),
               (340, 4), (342, 5), (344, 5), (346, 5), (348, 3), (350, 4)]

def index_swatches():
    """Grandes pastilles de l'index, normalisées par le blanc du papier de la page."""
    out, cid = {}, 1
    for pg, n in INDEX_PAGES:
        a = page_rgb(pg)
        right = a[:, int(a.shape[1] * .55):, :]
        mx, mn = right.max(2), right.min(2)
        ink = ((mx - mn) > 18) | ((255 - mx) > 45)
        prof = ink.mean(1)
        paper = np.percentile(right[prof <= .55].reshape(-1, 3), 85, axis=0)
        got = []
        for y0, y1 in runs(prof, .55, 20):
            cy = (y0 + y1) // 2
            reg = right[cy - 8:cy + 9, int(right.shape[1] * .2):int(right.shape[1] * .8)]
            got.append(np.median(reg.reshape(-1, 3), axis=0))
        ids = [153, 155] if pg == 348 else list(range(cid, cid + n))   # 154 = blanc
        assert len(got) == len(ids), (pg, len(got), len(ids))
        for i, rgb in zip(ids, got):
            out[i] = np.clip(np.array(rgb) / paper, 0, 1) * 255
        if pg == 348:
            out[154] = np.array([255., 255., 255.])
        cid += n
    return out

def paper_white(pno):
    a = page_rgb(pno)
    mx, mn = a.max(2), a.min(2)
    m = ((mx - mn) <= 12) & ((255 - mx) <= 45)
    return np.percentile(a[m].reshape(-1, 3), 85, axis=0)


# ---------------------------------------------------------------- 6. sortie
GROUPS = [(1, 38, 'reds', '赤・赤紫の色', 'Rouges & pourpres'),
          (39, 87, 'yellows', '黄・黄赤の色', 'Jaunes & orangés'),
          (88, 110, 'greens', '緑・黄緑の色', 'Verts & vert-jaunes'),
          (111, 133, 'blues', '青・青緑の色', 'Bleus & bleu-verts'),
          (134, 153, 'purples', '紫・青紫の色', 'Violets & bleu-violets'),
          (154, 159, 'neutrals', '白・灰・黒の色', 'Blancs, gris & noirs')]

def main():
    print('0. contrôle du catalogue')
    check_cmyk()
    print('1-3. lecture des planches')
    plates = collect_plates()
    emp, sig, _ = scan_model(plates)
    plates = assign(plates, emp, sig)
    print('4. contrôle par l’index inverse')
    plates = apply_book(plates, reverse_index(), emp, sig)

    print('5. mesure des couleurs')
    idx = index_swatches()
    whites, plate_samples = {}, {i: [] for i in range(1, N + 1)}
    for pl in plates:
        if pl['page'] not in whites:
            whites[pl['page']] = paper_white(pl['page'])
        for p in pl['picks']:
            plate_samples[p['i'] + 1].append(np.array(p['rgb']) / whites[pl['page']])

    grp = lambda i: next(k for a, b, k, _, _ in GROUPS if a <= i <= b)
    colors = []
    for c in COLORS:
        i = c['id']
        rgb = idx[i]
        if plate_samples[i]:
            rgb = .6 * (np.clip(np.median(plate_samples[i], 0), 0, 1) * 255) + .4 * rgb
        r, g, b = [int(round(v)) for v in np.clip(rgb, 0, 255)]
        colors.append(dict(id=i, name=c['en'], jp=c['jp'], kana=c['kana'],
                           hex='#%02X%02X%02X' % (r, g, b), rgb=[r, g, b],
                           cmyk=c['cmyk'], group=grp(i), count=len(plate_samples[i])))
    combos = [dict(id=pl['id'], size=pl['ncol'], colors=[p['i'] + 1 for p in pl['picks']])
              for pl in sorted(plates, key=lambda p: p['id'])]
    data = dict(
        source=dict(title='A Dictionary of Color Combinations',
                    jp='配色事典 — 大正・昭和の色彩ノート',
                    author='Sanzo Wada (和田三造, 1883-1967)',
                    publisher='Seigensha Art Publishing (2010), from Haishoku Soukan (1933-34)',
                    note="Valeurs CMJN relevées dans l'index du manuel; hex mesuré sur les "
                         "planches puis normalisé par le blanc du papier. Usage personnel."),
        groups=[dict(key=k, jp=jp, fr=fr, range=[a, b]) for a, b, k, jp, fr in GROUPS],
        colors=colors, combinations=combos)
    out = os.path.join(ROOT, 'data', 'omashing.json')
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print(f"→ {out} : {len(colors)} couleurs, {len(combos)} accords")

if __name__ == '__main__':
    main()
