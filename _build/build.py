"""Génère les tuiles SVG animées du README de profil (DA « vitrine » du portfolio).

    .venv/bin/pip install fonttools brotli pillow
    .venv/bin/python _build/build.py

Même DA que tobiasringot.vercel.app : grandes tuiles arrondies claires ou
sombres, trame de points, pixels qui mangent les bords, icônes en points,
Instrument Sans + JetBrains Mono. Polices sous-ensemblées et images intégrées
en base64 : GitHub affiche les SVG comme des images, sans ressources externes
ni JavaScript. Les animations sont en CSS/SMIL.

Objectif du profil : que les visiteurs suivent le compte et mettent une étoile
aux dépôts. Chaque tuile est un SVG à part, cliquable vers son projet.
"""

import base64
import io
import math
import pathlib
import random
import urllib.request

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageEnhance

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "_build" / "fonts"
MEDIA = pathlib.Path.home() / "Documents/ChatGPT/portfolio/public/media"
OUT = ROOT / "assets"

GF = "https://raw.githubusercontent.com/google/fonts/main/ofl"
SOURCES = {
    "InstrumentSans.ttf": f"{GF}/instrumentsans/InstrumentSans%5Bwdth%2Cwght%5D.ttf",
    "JetBrainsMono.ttf": f"{GF}/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
}

# Couleurs du portfolio (app/globals.css)
CADRE = "#0c0c0b"
CLAIR = "#ebeae6"
SOMBRE = "#151513"
ENCRE = "#141413"
GRIS = "#77746d"
GRIS_SOMBRE = "#8d8a82"
CREME = "#f2edc4"
ROUGE = "#d71921"
BLANC = "#ffffff"

M = 4  # marge transparente autour de chaque tuile (gouttière de 8 px entre deux)
R = 22  # rayon des tuiles


# ---------------------------------------------------------------- polices

class Font:
    def __init__(self, family, file, axes=None):
        self.family = family
        self.tt = TTFont(FONT_DIR / file)
        if axes:
            self.tt = instantiateVariableFont(self.tt, axes)
        self.cmap = self.tt.getBestCmap()
        self.hmtx = self.tt["hmtx"]
        self.upem = self.tt["head"].unitsPerEm
        buf = io.BytesIO()
        self.tt.save(buf)
        self.raw = buf.getvalue()

    def width(self, s, size, ls=0.0):
        total = 0
        for ch in s:
            gid = self.cmap.get(ord(ch))
            if gid is None:
                raise SystemExit(f"{self.family}: glyphe manquant {ch!r}")
            total += self.hmtx[gid][0]
        return total * size / self.upem + ls * size * len(s)

    def face(self, chars):
        opts = Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga", "calt"]
        sub = Subsetter(opts)
        sub.populate(text=chars + " ")
        font = TTFont(io.BytesIO(self.raw))
        sub.subset(font)
        font.flavor = "woff2"
        buf = io.BytesIO()
        font.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"@font-face{{font-family:{self.family};src:url(data:font/woff2;base64,{b64}) format('woff2')}}"


def load_fonts():
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        if not (FONT_DIR / name).exists():
            urllib.request.urlretrieve(url, FONT_DIR / name)
    return {
        "IS5": Font("IS5", "InstrumentSans.ttf", {"wght": 500, "wdth": 100}),
        "IS4": Font("IS4", "InstrumentSans.ttf", {"wght": 400, "wdth": 100}),
        "JB": Font("JB", "JetBrainsMono.ttf", {"wght": 500}),
    }


F = load_fonts()


# ---------------------------------------------------------------- outils

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, font, size, fill=ENCRE, anchor="start", ls=0.0, extra=""):
    ls_attr = f' letter-spacing="{ls * size:.2f}"' if ls else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}"{ls_attr} {extra}>{esc(s)}</text>')


def mono(x, y, s, fill=GRIS, anchor="start", size=12):
    """Étiquette en JetBrains Mono, capitales espacées (comme .mono du site)."""
    return text(x, y, s.upper(), "JB", size, fill, anchor, 0.12)


def mono_w(s, size=12):
    return F["JB"].width(s.upper(), size, 0.12)


def wrap(s, font, size, maxw, ls=0.0):
    lines, cur = [], ""
    for word in s.split():
        test = (cur + " " + word).strip()
        if F[font].width(test, size, ls) <= maxw:
            cur = test
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def lines(x, y, s, font, size, fill, maxw, lh, anchor="start", ls=0.0):
    out = [text(x, y + i * lh, l, font, size, fill, anchor, ls) for i, l in enumerate(wrap(s, font, size, maxw, ls))]
    return "".join(out), len(out)


def pill(x, y, label, style="noire", size=14, h=40, anchor="start", icon=None):
    """Pastille du site : noire, blanche, verre ou contour (sombre/clair)."""
    tw = F["IS5"].width(label, size, -0.01)
    iw = 18 if icon else 0
    w = tw + 40 + iw
    if anchor == "middle":
        x -= w / 2
    elif anchor == "end":
        x -= w
    fill, fg, stroke = {
        "noire": (ENCRE, BLANC, "none"),
        "noire-bord": (ENCRE, BLANC, "rgba(255,255,255,.22)"),
        "blanche": (BLANC, ENCRE, "none"),
        "bouton": (BLANC, ENCRE, "rgba(0,0,0,.14)"),
        "verre": ("rgba(255,255,255,.14)", BLANC, "rgba(255,255,255,.22)"),
        "contour-sombre": ("none", BLANC, "rgba(255,255,255,.25)"),
        "contour-clair": ("none", ENCRE, "rgba(0,0,0,.18)"),
    }[style]
    ic = ""
    if icon == "plus":
        cx, cy = x + 20 + 5, y + h / 2
        ic = (f'<path d="M{cx - 5} {cy} h10 M{cx} {cy - 5} v10" stroke="{fg}" stroke-width="1.8" stroke-linecap="round"/>')
    elif icon == "etoile":
        ic = star(x + 25, y + h / 2, 6.5, fg)
    body = (f'<rect x="{x + .5:.1f}" y="{y + .5:.1f}" width="{w - 1:.1f}" height="{h - 1}" rx="{h / 2}" '
            f'fill="{fill}" stroke="{stroke}"/>'
            + text(x + 20 + iw, y + h / 2 + size * .36, label, "IS5", size, fg, ls=-0.01))
    return ic and body + ic or body, w


def star(cx, cy, r, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * .45
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{fill}"/>'


def arrow(x, y, s, color, sw=1.8):
    """Flèche ↗ (x, y = coin bas-gauche)."""
    return (f'<path d="M{x} {y} L{x + s} {y - s} M{x + s * .3} {y - s} H{x + s} V{y - s * .7}" '
            f'stroke="{color}" stroke-width="{sw}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')


# Icônes en points (lib/points.ts du site)
MOTIFS = {
    "losange": ["....X....", "...XXX...", "..XX.XX..", ".XX.X.XX.", "XX.XXX.XX",
                ".XX.X.XX.", "..XX.XX..", "...XXX...", "....X...."],
    "anneau": ["...XXX...", ".XX...XX.", ".X.....X.", "X.......X", "X.......X",
               "X.......X", ".X.....X.", ".XX...XX.", "...XXX..."],
    "calques": ["....XXX....", "..XX...XX..", "XX.......XX", "..XX...XX..", "X...XXX...X",
                ".XX.....XX.", "...XX.XX...", ".....X....."],
    "fleche": ["...X...", "....X..", ".....X.", "XXXXXXX", ".....X.", "....X..", "...X..."],
    "coureur": [".........XXX..", ".........XXX..", ".........XXX..", "......XXXXX...",
                "....XXXXXXXX..", "...XX.XXXXX.XX", "..XX..XXXXX..X", ".......XXXXX..",
                "......XXX.XXX.", ".....XXX...XX.", "...XXX......XX", "..XX........X.",
                ".XX..........."],
    "coeur": [".XX...XX.", "XXXX.XXXX", "XXXXXXXXX", "XXXXXXXXX", ".XXXXXXX.",
              "..XXXXX..", "...XXX...", "....X...."],
}


def points(nom, cx, cy, pas, fill, r=None, anim=False, vague=False):
    """Icône en points, centrée sur (cx, cy). anim : les points s'allument un à un."""
    m = MOTIFS[nom]
    rows, cols = len(m), len(m[0])
    r = r or pas * .36
    out = []
    k = 0
    for j, row in enumerate(m):
        for i, c in enumerate(row):
            if c == "X":
                x = cx + (i - (cols - 1) / 2) * pas
                y = cy + (j - (rows - 1) / 2) * pas
                st = f' class="led" style="animation-delay:{.25 + k * .018:.2f}s"' if anim else ""
                if vague:
                    st = f' class="vague" style="animation-delay:{i * .12 + j * .05:.2f}s"'
                out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}"{st}/>')
                k += 1
    return "".join(out)


def pixels(x0, y0, w, h, coin, seed, palette, taille=22, portee=(.5, .55), anim=True):
    """Pixels qui mangent un coin de la tuile (coin : 'bd', 'bg', 'hd', 'hg')."""
    rnd = random.Random(seed)
    cols, rows = math.ceil(w / taille), math.ceil(h / taille)
    out = []
    for j in range(rows):
        for i in range(cols):
            fx = (cols - 1 - i) / cols if "d" in coin else i / cols
            fy = (rows - 1 - j) / rows if coin[0] == "b" else j / rows
            p = 1 - (fx / portee[0] + fy / portee[1])
            if p <= 0 or rnd.random() > p * 1.25:
                continue
            c = rnd.choice(palette)
            x, y = x0 + i * taille, y0 + j * taille
            cl = ""
            if anim and rnd.random() < .22:
                cl = f' class="blink" style="animation-delay:{rnd.random() * 4:.2f}s;animation-duration:{2.5 + rnd.random() * 3:.1f}s"'
            out.append(f'<rect x="{x}" y="{y}" width="{taille}" height="{taille}" fill="{c}"{cl}/>')
    return "".join(out)


def img_data(path, max_w=None, q=80, fmt="JPEG", sombre=1.0):
    path = pathlib.Path(path)
    if path.suffix == ".svg":
        return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode()
    im = Image.open(path)
    im = im.convert("RGBA" if fmt == "PNG" else "RGB")
    if max_w and im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    if sombre != 1.0:
        im = ImageEnhance.Brightness(im).enhance(sombre)
    buf = io.BytesIO()
    if fmt == "PNG":
        im.save(buf, "PNG", optimize=True)
    else:
        im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()


def image(x, y, w, h, data, fit="slice", extra=""):
    return (f'<image x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" href="{data}" '
            f'preserveAspectRatio="xMidYMid {fit}" {extra}/>')


CSS = """
.fade{animation:fade 1s cubic-bezier(.22,1,.36,1) both}
@keyframes fade{from{opacity:0;transform:translateY(18px)}}
.rise{animation:rise 1.1s cubic-bezier(.22,1,.36,1) both}
@keyframes rise{from{opacity:0;transform:translateY(60%)}}
.blink{animation:blink 3s ease-in-out infinite}
@keyframes blink{50%{opacity:0}}
.twinkle{animation:twinkle 4s ease-in-out infinite}
@keyframes twinkle{50%{opacity:.15}}
.led{animation:led .5s ease-out both}
@keyframes led{from{opacity:0}}
.bob{transform-box:fill-box;transform-origin:center;animation:bob 5s ease-in-out infinite}
@keyframes bob{50%{transform:translateY(-10px)}}
.zoom{transform-box:fill-box;transform-origin:center;animation:zoom 20s ease-in-out infinite alternate}
@keyframes zoom{to{transform:scale(1.07)}}
.flotte{transform-box:fill-box;transform-origin:center;animation:flotte 4.5s ease-in-out infinite}
@keyframes flotte{50%{transform:translateY(-6px)}}
.vague{animation:vague 3.2s ease-in-out infinite}
@keyframes vague{0%,60%,100%{opacity:1}30%{opacity:.25}}
.onde{transform-box:fill-box;transform-origin:center;animation:onde 2.6s cubic-bezier(.22,1,.36,1) infinite}
@keyframes onde{from{opacity:.55;transform:scale(1)}to{opacity:0;transform:scale(1.35,1.6)}}
.halo{animation:halo 6s ease-in-out infinite}
@keyframes halo{50%{opacity:.35}}
.court{animation:court 1.2s steps(2) infinite}
@keyframes court{50%{transform:translateX(3px)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def trame(id_, w, h, fill):
    return (f'<pattern id="{id_}" width="28" height="28" patternUnits="userSpaceOnUse">'
            f'<circle cx="14" cy="14" r="1.1" fill="{fill}"/></pattern>', f'<rect width="{w}" height="{h}" fill="url(#{id_})"/>')


def tile(w, h, body, fond=CLAIR, motif=None, defs="", css="", bordure=None):
    """Tuile arrondie posée avec une marge transparente ; polices intégrées."""
    iw, ih = w - 2 * M, h - 2 * M
    pat_def, pat = "", ""
    if motif:
        pat_def, pat = trame("trame", iw, ih, motif)
    used = [f for f in F if f'font-family="{f}"' in body]
    chars = "".join(sorted(set(body)))
    faces = "".join(F[f].face(chars) for f in used)
    bord = (f'<rect x="{M + .5}" y="{M + .5}" width="{iw - 1}" height="{ih - 1}" rx="{R - .5}" fill="none" '
            f'stroke="{bordure}"/>') if bordure else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
<style>{faces}{CSS}{css}</style>
<defs><clipPath id="arrondi"><rect width="{iw}" height="{ih}" rx="{R}"/></clipPath>{pat_def}{defs}</defs>
<g transform="translate({M} {M})"><g clip-path="url(#arrondi)"><rect width="{iw}" height="{ih}" fill="{fond}"/>{pat}{body}</g></g>{bord}
</svg>
'''


def legende(cx, y, surtitre, titre, resume, bouton, sombre_fond, maxw=440, titre_taille=34):
    """Légende centrée façon vitrine : mono, titre, résumé, pastille."""
    fg = BLANC if sombre_fond else ENCRE
    mut = "rgba(255,255,255,.7)" if sombre_fond else GRIS
    out = [mono(cx, y, surtitre, mut, "middle")]
    out.append(text(cx, y + 46, titre, "IS5", titre_taille, fg, "middle", -0.035))
    res, n = lines(cx, y + 80, resume, "IS4", 16, mut, maxw, 23, "middle")
    out.append(res)
    if bouton:
        p, _ = pill(cx, y + 80 + n * 23 + 4, bouton[0], bouton[1], anchor="middle")
        out.append(p)
    return f'<g class="fade" style="animation-delay:.3s">{"".join(out)}</g>'


# ---------------------------------------------------------------- tuiles

W = 1200


def hero():
    h = 620
    iw, ih = W - 2 * M, h - 2 * M
    fond = image(0, 0, iw, ih, img_data(MEDIA / "nuit.jpg", 1400, 72, sombre=.55), extra='class="zoom"')
    voile = (f'<rect width="{iw}" height="{ih}" fill="url(#voile)"/>')
    rnd = random.Random(7)
    etoiles = "".join(
        f'<circle class="twinkle" cx="{rnd.uniform(20, iw - 20):.0f}" cy="{rnd.uniform(20, ih * .62):.0f}" '
        f'r="{rnd.choice([1.6, 2, 2.4, 3])}" fill="#fff" opacity="{rnd.uniform(.35, .9):.2f}" '
        f'style="animation-delay:{rnd.uniform(0, 4):.2f}s;animation-duration:{rnd.uniform(3, 6):.1f}s"/>'
        for _ in range(46))
    cx = iw / 2
    titre, size, ls = "Tobias Ringot", 116, -0.048
    tw = F["IS5"].width(titre, size, ls)
    x = cx - tw / 2
    lettres = []
    for i, ch in enumerate(titre):
        lettres.append(f'<g class="rise" style="animation-delay:{.15 + i * .045:.2f}s">'
                       + text(x, 318, ch, "IS5", size, BLANC) + "</g>")
        x += F["IS5"].width(ch, size, ls)
    sous = (f'<g class="fade" style="animation-delay:.8s">'
            + text(cx, 376, "Je crée des sites internet avec Oculot Studio, je fais courir Aix", "IS4", 19, "rgba(255,255,255,.85)", "middle")
            + text(cx, 404, "avec NULLL.CLUB et je construis des logiciels créatifs avec Ooone.", "IS4", 19, "rgba(255,255,255,.85)", "middle")
            + "</g>")
    p1, w1 = pill(0, 0, "Suivre sur GitHub", "blanche", icon="plus")
    p2, w2 = pill(0, 0, "Plugins & MCP gratuits", "verre")
    gx = cx - (w1 + 10 + w2) / 2
    boutons = (f'<g class="fade" style="animation-delay:1s">'
               f'<g transform="translate({gx:.1f} 440)">{p1}</g>'
               f'<g transform="translate({gx + w1 + 10:.1f} 440)">{p2}</g></g>')
    haut = mono(cx, 196, "Entrepreneur · Aix-en-Provence", "rgba(255,255,255,.75)", "middle")
    bas = (mono(36, ih - 34, "43°31′ N · 5°27′ E", "rgba(255,255,255,.6)")
           + mono(iw - 36, ih - 34, "Suivez la suite ↓", "rgba(255,255,255,.75)", "end"))
    px = pixels(iw - 330, ih - 200, 330, 200, "bd", 3, [CADRE, CADRE, "#1d1d1b", "#2b2a27"], 22)
    defs = ('<linearGradient id="voile" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#0a1020" stop-opacity=".55"/>'
            '<stop offset=".6" stop-color="#0c0c0b" stop-opacity=".15"/>'
            '<stop offset="1" stop-color="#3a1d0e" stop-opacity=".55"/></linearGradient>')
    body = fond + voile + etoiles + f'<g class="fade">{haut}</g>' + "".join(lettres) + sous + boutons + bas + px
    return tile(W, h, body, CADRE, defs=defs)


def intro():
    h = 470
    iw, ih = W - 2 * M, h - 2 * M
    size = 40
    vign = {
        "oculot": ("img", img_data(MEDIA / "oculot-mark.svg"), BLANC, "meet"),
        "nulll": ("img", img_data(MEDIA / "nulll-apres-course-hd.webp", 240, 78), None, "slice"),
        "ooone": ("img", img_data(MEDIA / "affiche-ooone.webp", 240, 80), None, "slice"),
        "os": ("points", "losange", ENCRE, None),
    }
    rangs = [
        ["Je construis", ("oculot",), "un studio de refonte de sites,"],
        ["monté à trois,", ("nulll",), "un social run club à Aix et"],
        [("ooone",), "une suite de logiciels créatifs. Le reste"],
        ["du temps,", ("os",), "je publie des outils libres sur GitHub."],
    ]
    vw, vh = 66, 42
    acc = F["IS4"].width("{", size)
    sp = F["IS5"].width(" ", size, -0.03)

    def largeur(r):
        tot = 0
        for k, t in enumerate(r):
            if isinstance(t, tuple):
                tot += acc * 2 + vw + 12
            else:
                tot += F["IS5"].width(t, size, -0.03)
            if k < len(r) - 1:
                tot += sp
        return tot

    out = []
    y0 = 168
    for j, r in enumerate(rangs):
        y = y0 + j * 58
        x = iw / 2 - largeur(r) / 2
        seg = []
        for k, t in enumerate(r):
            if isinstance(t, tuple):
                kind, val, bg, fit = vign[t[0]]
                seg.append(text(x, y, "{", "IS4", size, "#a3a099"))
                vx = x + acc + 6
                vy = y - vh + 8
                clip = f"v{j}{k}"
                if kind == "img":
                    inner = (f'<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" rx="9" fill="{bg or "#ddd"}"/>'
                             + image(vx + (12 if fit == "meet" else 0), vy + (6 if fit == "meet" else 0),
                                     vw - (24 if fit == "meet" else 0), vh - (12 if fit == "meet" else 0), val, fit))
                else:
                    inner = (f'<rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" rx="9" fill="{ENCRE}"/>'
                             + points(val, vx + vw / 2, vy + vh / 2, 3.6, CREME, 1.3))
                out.append(f'<clipPath id="{clip}"><rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" rx="9"/></clipPath>')
                seg.append(f'<g class="flotte" style="animation-delay:{j * .6:.1f}s"><g clip-path="url(#{clip})">{inner}</g></g>')
                x = vx + vw + 6
                seg.append(text(x, y, "}", "IS4", size, "#a3a099"))
                x += acc
            else:
                seg.append(text(x, y, t, "IS5", size, ENCRE, ls=-0.03))
                x += F["IS5"].width(t, size, -0.03)
            x += sp
        out.append(f'<g class="fade" style="animation-delay:{.15 + j * .12:.2f}s">{"".join(seg)}</g>')
    tete = mono(iw / 2, 92, "Ce que je construis", GRIS, "middle")
    return tile(W, h, tete + "".join(out), CLAIR, motif="rgba(0,0,0,.2)")


TW = W // 2  # largeur d'une demi-tuile (600 px, 592 visibles)
TH = 600


def oculot():
    iw, ih = TW - 2 * M, TH - 2 * M
    logo = image(iw / 2 - 170, 150, 340, 120, img_data(MEDIA / "oculot-logo-complet-creme.svg"), "meet")
    leg = legende(iw / 2, 372, "Studio web · Actif", "Oculot Studio",
                  "Un studio de refonte de sites internet, monté à trois avec Tom et Eliott.",
                  ("oculot.studio ↗", "contour-sombre"), True, 420)
    px = pixels(0, 0, 200, 130, "hg", 21, [CADRE, "#232321", "#2f2e2b"], 22)
    return tile(TW, TH, px + logo + leg, SOMBRE, motif="rgba(255,255,255,.13)", bordure="rgba(255,255,255,.08)")


def sites():
    iw, ih = TW - 2 * M, TH - 2 * M
    defs, css, body = [], [], []
    # MacBook
    sx, sy, sw, sh = 46, 58, 404, 252
    pw = img_data(ROOT.parent / "Documents/ChatGPT/portfolio/public/media/oculot/pompom.webp", 808, 74)
    ph_img = round(sw * 3750 / 1200)
    defs.append(f'<clipPath id="ecran"><rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="6"/></clipPath>')
    css.append(f".dmac{{animation:dmac 22s ease-in-out infinite alternate}}@keyframes dmac{{0%,8%{{transform:translateY(0)}}92%,100%{{transform:translateY(-{ph_img - sh}px)}}}}")
    body.append(f'<g class="flotte" style="animation-duration:7s">'
                f'<rect x="{sx - 10}" y="{sy - 10}" width="{sw + 20}" height="{sh + 26}" rx="16" fill="#0d0d0d" stroke="#767a7d" stroke-width="1.5"/>'
                f'<g clip-path="url(#ecran)"><g class="dmac">{image(sx, sy, sw, ph_img, pw, "meet")}</g></g>'
                f'<rect x="{sx + sw / 2 - 26}" y="{sy - 10}" width="52" height="9" rx="4" fill="#0d0d0d"/>'
                f'<path d="M{sx - 34} {sy + sh + 16} h{sw + 68} l-10 12 h-{sw + 48} z" fill="#83878a"/>'
                f'<rect x="{sx + sw / 2 - 40}" y="{sy + sh + 16}" width="80" height="5" rx="2.5" fill="#6a6d70"/></g>')
    # iPhone
    tx, ty, tw, th = 404, 128, 132, 272
    nw = img_data(ROOT.parent / "Documents/ChatGPT/portfolio/public/media/oculot/nulll-m.webp", 264, 76)
    nh = round((tw - 12) * 8440 / 780)
    defs.append(f'<clipPath id="tel"><rect x="{tx + 6}" y="{ty + 6}" width="{tw - 12}" height="{th - 12}" rx="20"/></clipPath>')
    css.append(f".dtel{{animation:dtel 28s ease-in-out infinite alternate;animation-delay:-6s}}@keyframes dtel{{0%,8%{{transform:translateY(0)}}92%,100%{{transform:translateY(-{nh - th + 12}px)}}}}")
    body.append(f'<g class="flotte" style="animation-duration:6s;animation-delay:-2s">'
                f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="26" fill="#010101" stroke="#342c3f" stroke-width="2"/>'
                f'<g clip-path="url(#tel)"><g class="dtel">{image(tx + 6, ty + 6, tw - 12, nh, nw, "meet")}</g></g>'
                f'<rect x="{tx + tw / 2 - 20}" y="{ty + 14}" width="40" height="12" rx="6" fill="#010101"/></g>')
    leg = (f'<g class="fade" style="animation-delay:.3s">'
           + mono(iw / 2, 456, "Sites réalisés par le studio", GRIS, "middle")
           + text(iw / 2, 500, "Studio POMPOM, NULLL.CLUB", "IS5", 30, ENCRE, "middle", -0.035)
           + pill(iw / 2, 522, "Voir le studio ↗", "noire", anchor="middle")[0] + "</g>")
    return tile(TW, TH, "".join(body) + leg, CLAIR, motif="rgba(0,0,0,.2)", defs="".join(defs), css="".join(css))


def nulll():
    iw, ih = TW - 2 * M, TH - 2 * M
    photo = image(0, 0, iw, ih, img_data(MEDIA / "nulll-apres-course-hd.webp", 900, 78), extra='class="zoom"')
    voile = f'<rect width="{iw}" height="{ih}" fill="url(#bas)"/>'
    logo_d = img_data(MEDIA / "nulll-logo-creme.png", 600, fmt="PNG")
    logo = image(36, ih - 222, 330, 64, logo_d, "meet", 'preserveAspectRatio="xMinYMid meet"')
    logo = logo.replace('preserveAspectRatio="xMidYMid meet" ', "")
    txt = (f'<g class="fade" style="animation-delay:.3s">'
           + mono(36, ih - 236, "Social run club · Aix-en-Provence", "rgba(255,255,255,.8)")
           + logo
           + lines(36, ih - 128, "Un social run club à Aix-en-Provence. La course sert de prétexte, le but est de se rencontrer.",
                   "IS4", 16, "rgba(255,255,255,.88)", 380, 23)[0]
           + pill(36, ih - 84, "nulll.club ↗", "verre")[0] + "</g>")
    px = pixels(iw - 260, ih - 176, 260, 176, "bd", 11, [CADRE, CADRE, "#1d1d1b", "#2f2e2b", "#5d5b56"], 22)
    defs = ('<linearGradient id="bas" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset=".35" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#000" stop-opacity=".78"/></linearGradient>')
    return tile(TW, TH, photo + voile + txt + px, CADRE, defs=defs)


def ooone():
    iw, ih = TW - 2 * M, TH - 2 * M
    ic = img_data(MEDIA / "icones/ooone.webp", 500, fmt="PNG")
    ombre = (f'<ellipse cx="{iw / 2}" cy="318" rx="110" ry="14" fill="#000" opacity=".12" filter="url(#flou)"/>')
    halo = f'<circle class="halo" cx="{iw / 2}" cy="190" r="150" fill="url(#lueur)"/>'
    icone = f'<g class="bob">{image(iw / 2 - 120, 70, 240, 240, ic, "meet")}</g>'
    leg = legende(iw / 2, 378, "Logiciels créatifs · Bêta fermée", "Ooone",
                  "Une suite créative complète : photo, retouche, design, rendu d'architecture, vidéo et 3D.",
                  ("Suivre la bêta ↗", "noire"), False, 420)
    defs = '<filter id="flou"><feGaussianBlur stdDeviation="8"/></filter>'
    defs += ('<radialGradient id="lueur"><stop offset="0" stop-color="#c04ee0" stop-opacity=".28"/>'
             '<stop offset=".6" stop-color="#e9a04a" stop-opacity=".1"/><stop offset="1" stop-color="#e9a04a" stop-opacity="0"/></radialGradient>')
    return tile(TW, TH, halo + ombre + icone + leg, CLAIR, defs=defs)


def apps():
    iw, ih = TW - 2 * M, TH - 2 * M
    liste = [("Rawww", "rawww", "Bêta"), ("Layer", "layer", "Bêta"), ("Reeel", "reeel", "À venir"),
             ("Wire", "wire", "À venir"), ("Arch", "arch", "À venir"), ("Blob 3D", "blob", "À venir")]
    out = []
    s, gx, gy = 84, 116, 150
    x0 = iw / 2 - gx
    for k, (nom, f, etat) in enumerate(liste):
        cx = x0 + (k % 3) * gx
        cy = 118 + (k // 3) * gy
        d = img_data(MEDIA / f"icones/{f}.webp", 200, fmt="PNG")
        out.append(f'<g class="fade" style="animation-delay:{.15 + k * .09:.2f}s">'
                   + f'<g class="flotte" style="animation-delay:{k * .45:.2f}s">' + image(cx - s / 2, cy - s / 2, s, s, d, "meet") + "</g>"
                   + mono(cx, cy + s / 2 + 22, nom, BLANC, "middle", 11)
                   + mono(cx, cy + s / 2 + 40, etat, GRIS_SOMBRE, "middle", 11) + "</g>")
    leg = (f'<g class="fade" style="animation-delay:.6s">'
           + mono(iw / 2, 430, "Rawww et Layer en bêta · 4 apps à venir", "rgba(255,255,255,.7)", "middle")
           + text(iw / 2, 474, "Simple by default.", "IS5", 34, BLANC, "middle", -0.035)
           + text(iw / 2, 512, "Deep when you want.", "IS5", 34, BLANC, "middle", -0.035)
           + "</g>")
    return tile(TW, TH, "".join(out) + leg, SOMBRE, motif="rgba(255,255,255,.13)", bordure="rgba(255,255,255,.08)")


def opensource_tete():
    h = 300
    iw, ih = W - 2 * M, h - 2 * M
    t = (f'<g class="fade">'
         + mono(40, 70, "Gratuit · Open source · Sans clé API", "rgba(255,255,255,.6)")
         + text(38, 140, "Plugins et MCP gratuits, pour tout le monde.", "IS5", 50, BLANC, ls=-0.04)
         + text(40, 188, "Plugins Claude Code et serveurs MCP que je fabrique en chemin, libres et prêts", "IS4", 18, "rgba(255,255,255,.7)")
         + text(40, 214, "à installer en une commande. Une étoile sur un dépôt m'aide à continuer.", "IS4", 18, "rgba(255,255,255,.7)")
         + "</g>")
    p, w = pill(iw - 40, 186, "Mettre une étoile", "blanche", anchor="end", icon="etoile")
    ic = points("losange", iw - 90, 92, 7, CREME, 2.4, vague=True)
    return tile(W, h, t + f'<g class="fade" style="animation-delay:.4s">{p}</g>' + ic, SOMBRE,
                motif="rgba(255,255,255,.13)", bordure="rgba(255,255,255,.08)")


DEPOTS_MUE = [
    ("mue", "Outil", "fleche", "Réécrit du COBOL en Java et prouve que les deux donnent exactement les mêmes résultats.",
     "TypeScript", "#3178c6", "AGPL-3.0"),
]
DEPOTS = [
    ("france-mcp", "Serveur MCP", "calques", "L'État français branché sur l'IA : Sirene, BOAMP, DVF, cadastre, DPE… 19 outils, zéro clé API.",
     "JavaScript", "#f1e05a", "MIT"),
    ("claude-ovh-dns", "Plugin Claude Code", "losange", "Pointez un domaine OVH vers Vercel en trois commandes, sans jamais casser vos e-mails.",
     "Python", "#3572A5", "MIT"),
] + DEPOTS_MUE


def depot(i):
    nom, kind, motif, desc, lang, couleur, lic = DEPOTS[i]
    w, h = 400, 300
    iw, ih = w - 2 * M, h - 2 * M
    ic = (f'<rect x="28" y="28" width="38" height="38" rx="10" fill="#22221f"/>'
          + points(motif, 47, 47, 3.4, CREME, 1.2, vague=True))
    body = (ic + mono(80, 52, kind, "rgba(255,255,255,.75)")
            + text(28, 116, nom, "JB", 22, BLANC, ls=-0.02)
            + lines(28, 152, desc, "IS4", 15, "rgba(255,255,255,.68)", iw - 56, 22)[0]
            + f'<circle cx="34" cy="{ih - 40}" r="5" fill="{couleur}"/>'
            + mono(48, ih - 36, f"{lang} · {lic}", "rgba(255,255,255,.6)", size=11))
    p, _ = pill(iw - 24, ih - 60, "Star", "contour-sombre", 13, 36, "end", icon="etoile")
    return tile(w, h, f'<g class="fade" style="animation-delay:{.1 + i * .12:.2f}s">{body}{p}</g>', "#1a1a18",
                bordure="rgba(255,255,255,.1)")


def suivre():
    h = 520
    iw, ih = W - 2 * M, h - 2 * M
    ic = points("coureur", iw / 2, 112, 6.2, ENCRE, 2.3, anim=True)
    t = (f'<g class="fade" style="animation-delay:.2s">'
         + mono(iw / 2, 196, "Restons en contact", GRIS, "middle")
         + text(iw / 2, 272, "Suivez la suite.", "IS5", 76, ENCRE, "middle", -0.048)
         + text(iw / 2, 322, "Nouvelles apps Ooone, outils libres, sites du studio, sorties du club :", "IS4", 19, GRIS, "middle")
         + text(iw / 2, 350, "je publie tout ici, au fur et à mesure.", "IS4", 19, GRIS, "middle")
         + "</g>")
    p1, w1 = pill(0, 0, "Suivre @tbsrgt", "noire", 15, 46, icon="plus")
    p2, w2 = pill(0, 0, "Journal · RSS", "contour-clair", 15, 46)
    p3, w3 = pill(0, 0, "Portfolio ↗", "contour-clair", 15, 46)
    gx = iw / 2 - (w1 + w2 + w3 + 20) / 2
    b = (f'<g class="fade" style="animation-delay:.45s">'
         f'<g transform="translate({gx:.1f} 392)">{p1}</g>'
         f'<g transform="translate({gx + w1 + 10:.1f} 392)">{p2}</g>'
         f'<g transform="translate({gx + w1 + w2 + 20:.1f} 392)">{p3}</g></g>')
    px = (pixels(0, 0, 260, 150, "hg", 5, [CADRE, "#2b2a27", "#5d5b56", "#cfcdc7"], 22)
          + pixels(iw - 260, ih - 150, 260, 150, "bd", 9, [CADRE, "#2b2a27", "#5d5b56", "#cfcdc7"], 22))
    return tile(W, h, ic + t + b + px, CLAIR, motif="rgba(0,0,0,.2)")


def bouton(label, style, icon=None):
    size, h = 14, 42
    p, w = pill(1, 1, label, style, size, h - 2, icon=icon)
    w += 2
    used = "".join(sorted(set(label)))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.1f} {h}" width="{w:.1f}" height="{h}">'
            f'<style>{F["IS5"].face(used)}</style>{p}</svg>\n')


BOUTONS = {
    "btn-suivre": ("Suivre sur GitHub", "noire-bord", "plus"),
    "btn-portfolio": ("Portfolio ↗", "bouton", None),
    "btn-journal": ("Journal ↗", "bouton", None),
    "btn-instagram": ("Instagram ↗", "bouton", None),
    "btn-linkedin": ("LinkedIn ↗", "bouton", None),
}


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    tuiles = {"hero": hero, "intro": intro, "oculot": oculot, "sites": sites, "nulll": nulll, "ooone": ooone,
              "opensource": opensource_tete, "suivre": suivre}
    for nom, fn in tuiles.items():
        (OUT / f"{nom}.svg").write_text(fn())
    for i, d in enumerate(DEPOTS):
        (OUT / f"depot-{d[0]}.svg").write_text(depot(i))
    for nom, (label, style, icon) in BOUTONS.items():
        (OUT / f"{nom}.svg").write_text(bouton(label, style, icon))
    # Noms suffixés par l'empreinte du contenu : GitHub met les images en cache,
    # un nouveau nom force l'affichage de la nouvelle version.
    import hashlib
    import re
    noms = {}
    for p in sorted(OUT.glob("*.svg")):
        h = hashlib.sha1(p.read_bytes()).hexdigest()[:8]
        cible = OUT / f"{p.stem}-{h}.svg"
        p.rename(cible)
        noms[p.stem] = cible.name
        print(f"{cible.name:34} {cible.stat().st_size / 1024:7.1f} Ko")
    readme = ROOT / "README.md"
    txt = readme.read_text()
    txt = re.sub(r"\./assets/([a-z-]+?)(?:-[0-9a-f]{8})?\.svg(?:\?v=\d+)?",
                 lambda m: f"./assets/{noms[m.group(1)]}", txt)
    readme.write_text(txt)


if __name__ == "__main__":
    main()
