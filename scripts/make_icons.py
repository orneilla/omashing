#!/usr/bin/env python3
"""Génère les icônes de l'application à partir de la palette du manuel.

Le motif reprend la disposition en croix des planches à quatre couleurs.

    pip install pillow
    python3 scripts/make_icons.py
"""
import json, os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = json.load(open(os.path.join(ROOT, 'data', 'omashing.json'), encoding='utf-8'))
BY_ID = {c['id']: c for c in DATA['colors']}

PAPER = '#E9E9E6'
# haut, gauche, droite, bas — Yellow Orange, Cerulian Blue, Carmine, Deep Indigo
CROSS = [62, 118, 23, 132]

def draw(size, inset=0.0):
    img = Image.new('RGB', (size, size), PAPER)
    d = ImageDraw.Draw(img)
    top, left, right, bottom = (BY_ID[i]['hex'] for i in CROSS)
    m = size * inset
    S, E = m, size - m          # bornes du motif
    w = E - S
    cx0, cx1 = S + w * .29, S + w * .71      # colonne verticale
    by0, by1 = S + w * .33, S + w * .67      # bande horizontale
    d.rectangle([cx0, S, cx1, S + w / 2], fill=top)
    d.rectangle([cx0, S + w / 2, cx1, E], fill=bottom)
    d.rectangle([S, by0, S + w / 2, by1], fill=left)
    d.rectangle([S + w / 2, by0, E, by1], fill=right)
    return img

out = os.path.join(ROOT, 'icons')
os.makedirs(out, exist_ok=True)
for name, size, inset in [('icon-192.png', 192, .06), ('icon-512.png', 512, .06),
                          ('apple-touch-icon.png', 180, .10),
                          ('maskable-512.png', 512, .21)]:
    draw(size, inset).save(os.path.join(out, name))
    print('icons/' + name)
