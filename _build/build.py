"""Génère les cartes SVG animées du README de profil (charte Oculot).

    python3 -m venv .venv && .venv/bin/pip install fonttools brotli
    .venv/bin/python _build/build.py

Les polices (OFL, Google Fonts) sont téléchargées dans _build/fonts puis
sous-ensemblées et intégrées en base64 dans chaque SVG : GitHub affiche les
SVG comme des images, sans accès aux polices externes ni au JavaScript. Les
effets (lettres qui montent, gribouillis qui se tracent, badges qui tournent,
bandeaux qui défilent) sont donc faits en CSS/SMIL.

Charte : crème / encre / tomate / beurre / rose, Bricolage Grotesque pour les
titres, DM Sans pour le texte, Gochi Hand pour les notes à la main, étoile
Oculot à quatre branches molles.
"""

import base64
import io
import math
import pathlib
import urllib.request

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "_build" / "fonts"
OUT = ROOT / "assets"

GF = "https://raw.githubusercontent.com/google/fonts/main/ofl"
SOURCES = {
    "BricolageGrotesque.ttf": f"{GF}/bricolagegrotesque/BricolageGrotesque%5Bopsz%2Cwdth%2Cwght%5D.ttf",
    "DMSans.ttf": f"{GF}/dmsans/DMSans%5Bopsz%2Cwght%5D.ttf",
    "GochiHand-Regular.ttf": f"{GF}/gochihand/GochiHand-Regular.ttf",
    "JetBrainsMono.ttf": f"{GF}/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
}

W = 1200
CREAM = "#F5EFE3"
PAPER = "#FBF8F2"
INK = "#15130F"
TOMATO = "#FF5B37"
BUTTER = "#FFD65C"
PINK = "#F7C3D4"
MUTED = "#6F6A60"
LINE = "#15130F1F"
LINE_DARK = "#F5EFE326"


# ---------------------------------------------------------------- fonts

class Font:
    def __init__(self, family, file, axes=None):
        self.family = family
        self.tt = TTFont(FONT_DIR / file)
        if axes:
            self.tt = instantiateVariableFont(self.tt, axes)
        self.cmap = self.tt.getBestCmap()
        self.hmtx = self.tt["hmtx"]
        self.upem = self.tt["head"].unitsPerEm

    def width(self, s, size, ls=0.0):
        """Largeur en px, ls en em (letter-spacing)."""
        total = 0
        for ch in s:
            gid = self.cmap.get(ord(ch))
            if gid is None:
                raise SystemExit(f"{self.family}: glyphe manquant {ch!r}")
            total += self.hmtx[gid][0]
        return total * size / self.upem + ls * size * len(s)

    def face(self, text):
        buf = io.BytesIO()
        opts = Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga", "calt"]
        sub = Subsetter(opts)
        sub.populate(text=text + " ")
        font = TTFont(io.BytesIO(self._raw()))
        sub.subset(font)
        font.flavor = "woff2"
        font.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"@font-face{{font-family:{self.family};src:url(data:font/woff2;base64,{b64}) format('woff2')}}"

    def _raw(self):
        buf = io.BytesIO()
        self.tt.save(buf)
        return buf.getvalue()


def load_fonts():
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        if not (FONT_DIR / name).exists():
            urllib.request.urlretrieve(url, FONT_DIR / name)
    return {
        "BG8": Font("BG8", "BricolageGrotesque.ttf", {"wght": 800, "opsz": 96, "wdth": 90}),
        "BG7": Font("BG7", "BricolageGrotesque.ttf", {"wght": 700, "opsz": 48, "wdth": 100}),
        "DM": Font("DM", "DMSans.ttf", {"wght": 400, "opsz": 14}),
        "DM5": Font("DM5", "DMSans.ttf", {"wght": 500, "opsz": 14}),
        "DM6": Font("DM6", "DMSans.ttf", {"wght": 600, "opsz": 14}),
        "GH": Font("GH", "GochiHand-Regular.ttf"),
        "JB": Font("JB", "JetBrainsMono.ttf", {"wght": 500}),
    }


F = load_fonts()


# ---------------------------------------------------------------- helpers

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, font, size, fill=INK, anchor="start", ls=0.0, extra=""):
    ls_attr = f' letter-spacing="{ls * size:.2f}"' if ls else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}"{ls_attr} {extra}>{esc(s)}</text>')


def small(x, y, s, fill=MUTED, anchor="start", size=13):
    """Petite étiquette en capitales espacées (DM Sans 600)."""
    return text(x, y, s.upper(), "DM6", size, fill, anchor, 0.1)


def small_w(s, size=13):
    return F["DM6"].width(s.upper(), size, 0.1)


# Étoile Oculot : quatre branches un peu molles, boîte 100 × 100.
STAR_D = ("M50 3c4 20 9 33 17 40s17 9 30 7c-13 3-22 7-29 14s-12 21-18 33"
          "c-4-13-9-25-17-32S14 54 3 50c12-2 22-5 29-12S46 21 50 3Z")


def star(cx, cy, r, fill, extra=""):
    s = r / 50
    return (f'<g transform="translate({cx - r:.1f} {cy - r:.1f}) scale({s:.4f})"{extra}>'
            f'<path d="{STAR_D}" fill="{fill}"/></g>')


# Le « o » du logo : tracé de la police, étoile en pupille avec un liseré de la couleur du fond.
O_D = ("M258 -14Q184 -14 132.0 18.0Q80 50 52.5 112.0Q25 174 25 265Q25 360 54.0 421.5Q83 483 136.0 512.5"
       "Q189 542 260 542Q334 542 386.5 512.0Q439 482 466.5 421.5Q494 361 494 268Q494 170 464.5 108.0"
       "Q435 46 382.0 16.0Q329 -14 258 -14ZM261 102Q286 102 302.5 118.5Q319 135 327.0 169.0Q335 203 335 256"
       "Q335 312 326.5 348.5Q318 385 301.0 403.5Q284 422 257 422Q233 422 216.5 405.0Q200 388 192.0 352.5"
       "Q184 317 184 261Q184 179 203.5 140.5Q223 102 261 102Z")


def mark(x, y, size, o_fill, star_fill, bg):
    """Symbole Oculot dans une boîte size × size (coin haut-gauche x, y)."""
    s = size / 720
    return (f'<g transform="translate({x:.1f} {y:.1f}) scale({s:.5f}) translate(100.5 82)">'
            f'<path fill="{o_fill}" transform="translate(0 542) scale(1 -1)" d="{O_D}"/>'
            f'<g transform="translate(133.97 155.47) scale(2.5106)">'
            f'<path d="{STAR_D}" fill="{bg}" stroke="{bg}" stroke-width="13.54" stroke-linejoin="round"/>'
            f'<path d="{STAR_D}" fill="{star_fill}"/></g></g>')


def underline(x1, x2, y, color, delay=0.6, sw=5):
    """Soulignement à la main (deux traits qui ondulent), tracé à l'écran."""
    dx = x2 - x1
    d1 = f"M{x1:.1f} {y:.1f} q{dx * .25:.1f} -8 {dx * .5:.1f} -1 t{dx * .5:.1f} -2"
    d2 = f"M{x1 + 14:.1f} {y + 9:.1f} q{dx * .3:.1f} 6 {dx * .55:.1f} 0 t{dx * .4:.1f} -3"
    return (f'<path class="draw" style="animation-delay:{delay:.2f}s" d="{d1}" stroke="{color}" '
            f'stroke-width="{sw}" fill="none" stroke-linecap="round" pathLength="1"/>'
            f'<path class="draw" style="animation-delay:{delay + .25:.2f}s" d="{d2}" stroke="{color}" '
            f'stroke-width="{sw * .7:.1f}" fill="none" stroke-linecap="round" pathLength="1"/>')


def ring(cx, cy, rx, ry, color, delay=0.8, sw=4, rot=-6):
    """Cercle gribouillé autour d'un mot, pas tout à fait fermé."""
    d = (f"M{cx - rx:.1f} {cy:.1f} a{rx:.1f} {ry:.1f} 0 1 1 {2 * rx:.1f} 0 "
         f"a{rx * 1.04:.1f} {ry * 1.1:.1f} 0 1 1 {-2 * rx - 18:.1f} {-8:.1f}")
    return (f'<path class="draw" style="animation-delay:{delay:.2f}s" d="{d}" stroke="{color}" '
            f'stroke-width="{sw}" fill="none" stroke-linecap="round" pathLength="1" '
            f'transform="rotate({rot} {cx} {cy})"/>')


def hand_arrow(x, y, dx, dy, color, delay=1.0, sw=4):
    """Flèche courbe à la main de (x, y) vers (x + dx, y + dy)."""
    cx, cy = x + dx * .15, y + dy * .95
    ex, ey = x + dx, y + dy
    ang = math.atan2(ey - cy, ex - cx)
    a1 = ang + math.radians(150)
    a2 = ang - math.radians(150)
    h = 16
    head = (f"M{ex + h * math.cos(a1):.1f} {ey + h * math.sin(a1):.1f} L{ex:.1f} {ey:.1f} "
            f"L{ex + h * math.cos(a2):.1f} {ey + h * math.sin(a2):.1f}")
    return (f'<path class="draw" style="animation-delay:{delay:.2f}s" d="M{x:.1f} {y:.1f} Q{cx:.1f} {cy:.1f} {ex:.1f} {ey:.1f}" '
            f'stroke="{color}" stroke-width="{sw}" fill="none" stroke-linecap="round" pathLength="1"/>'
            f'<path class="draw" style="animation-delay:{delay + .35:.2f}s" d="{head}" stroke="{color}" '
            f'stroke-width="{sw}" fill="none" stroke-linecap="round" stroke-linejoin="round" pathLength="1"/>')


def pill(x, y, label, fill, fg, size=13, h=40, stroke=None, dot=None, delay=None):
    w = small_w(label, size) + 44 + (18 if dot else 0)
    st = f' stroke="{stroke}"' if stroke else ""
    cls = f' class="fade" style="animation-delay:{delay:.2f}s"' if delay is not None else ""
    d = f'<circle cx="{x + 24:.1f}" cy="{y + h / 2:.1f}" r="4.5" fill="{dot}"/>' if dot else ""
    return (f'<g{cls}><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{fill}"{st}/>'
            + d + small(x + 22 + (18 if dot else 0), y + h / 2 + 5, label, fg, size=size) + "</g>"), w


def arrow(x, y, s, color, sw=2.4):
    """Flèche ↗ (x, y = coin bas-gauche)."""
    return (f'<path d="M{x} {y} L{x + s} {y - s} M{x + s * .3} {y - s} H{x + s} V{y - s * .7}" '
            f'stroke="{color}" stroke-width="{sw}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')


def badge(cx, cy, r, words, disk, fg, center_fill, dur=16, size=13):
    """Badge rond qui tourne, texte sur le cercle, étoile au centre."""
    circ = 2 * math.pi * r
    return (f'<circle cx="{cx}" cy="{cy}" r="{r + 26}" fill="{disk}"/>'
            f'<g class="spin" style="transform-origin:{cx}px {cy}px">'
            f'<path id="ring{cx}" d="M{cx - r} {cy} a{r} {r} 0 1 1 {2 * r} 0 a{r} {r} 0 1 1 {-2 * r} 0" fill="none"/>'
            f'<text font-family="DM6" font-size="{size}" fill="{fg}" textLength="{circ - 4:.1f}" lengthAdjust="spacing">'
            f'<textPath href="#ring{cx}">{esc(words.upper())}</textPath></text></g>'
            + star(cx, cy, r * .42, center_fill, ' class="wobble"'))


BASE_CSS = """
.fade{animation:fade 1s cubic-bezier(.2,.8,.2,1) both}
@keyframes fade{from{opacity:0;transform:translateY(22px)}}
.rise{animation:rise 1.1s cubic-bezier(.2,.8,.2,1) both}
@keyframes rise{from{transform:translateY(260px)}}
.draw{stroke-dasharray:1;stroke-dashoffset:1;animation:draw .9s cubic-bezier(.5,0,.2,1) forwards}
@keyframes draw{to{stroke-dashoffset:0}}
.spin{animation:spin 16s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
.wobble{transform-box:fill-box;transform-origin:center;animation:wobble 3.2s ease-in-out infinite}
@keyframes wobble{50%{transform:rotate(14deg) scale(1.08)}}
.pulse{animation:pulse 1.6s ease-in-out infinite}@keyframes pulse{50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}.draw{stroke-dashoffset:0}}
"""


def grain(id_="grain", opacity=0.05, h=800):
    return (f'<filter id="{id_}"><feTurbulence type="fractalNoise" baseFrequency=".85" '
            f'numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  '
            f'0 0 0 0 0  0 0 0 .9 0"/></filter>'
            f'<rect width="{W}" height="{h}" filter="url(#{id_})" opacity="{opacity}"/>')


def card(h, body, css="", defs="", bg=CREAM, label=None, dark=False):
    """Carte arrondie, polices intégrées pour tout le texte utilisé."""
    head = ""
    fg = CREAM if dark else INK
    mut = "#B8B1A3" if dark else MUTED
    line = LINE_DARK if dark else LINE
    if label:
        num, title, right = label
        head = (small(40, 52, num, TOMATO) + small(96, 52, title, fg) + small(W - 40, 52, right, mut, "end")
                + f'<line x1="40" y1="74" x2="{W - 40}" y2="74" stroke="{line}"/>')
    inner = head + body
    used = set(f for f in F if f'font-family="{f}"' in inner)
    faces = "".join(F[f].face("".join(sorted(set(inner)))) for f in used)
    back = (f'<rect width="{W}" height="{h}" fill="{bg}"/>' + grain(h=h)) if bg else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}">
<style>{faces}{BASE_CSS}{css}</style>
<defs><clipPath id="round"><rect width="{W}" height="{h}" rx="{28 if bg else 0}"/></clipPath>{defs}</defs>
<g clip-path="url(#round)">{back}{inner}</g>
</svg>
'''


def split(x, y, word, font, size, ls, delay0, step, fill):
    """Chaque lettre monte depuis un masque, en décalé."""
    out, cx = [], x
    for i, ch in enumerate(word):
        out.append(f'<g class="rise" style="animation-delay:{delay0 + i * step:.2f}s">'
                   + text(cx, y, ch, font, size, fill) + "</g>")
        cx += F[font].width(ch, size, ls)
    return "".join(out), cx


# ---------------------------------------------------------------- cartes

def hero():
    h = 690
    top = (small(40, 58, "Tobias Ringot ©2026", INK)
           + small(40 + 1120 / 3, 58, "Web designer & développeur")
           + small(40 + 2240 / 3, 58, "Aix-en-Provence, FR")
           + small(W - 40, 58, "Dispo pour projets", INK, "end")
           + f'<circle class="pulse" cx="{W - 40 - small_w("Dispo pour projets") - 14:.1f}" cy="53.5" r="4.5" fill="{TOMATO}"/>'
           + f'<line x1="40" y1="82" x2="{W - 40}" y2="82" stroke="{LINE}"/>')
    size, ls = 212, -0.045
    l1, end1 = split(34, 318, "Tobias", "BG8", size, ls, .15, .06, INK)
    l2, end2 = split(34, 522, "Ringot", "BG8", size, ls, .45, .06, TOMATO)
    deco = (underline(40, end2 - 10, 548, BUTTER, 1.0, 9)
            + f'<g class="fade" style="animation-delay:1.1s">'
            + text(end1 + 56, 262, "co-fondateur", "GH", 40, INK)
            + text(end1 + 56, 306, "d'Oculot Studio", "GH", 40, TOMATO) + "</g>"
            + hand_arrow(end1 + 150, 322, 60, 70, TOMATO, 1.4)
            + f'<g class="fade" style="animation-delay:.9s">'
            + badge(1058, 450, 70, "Audit gratuit • Parlons de votre site • ", BUTTER, INK, TOMATO) + "</g>")
    bottom = (f'<g class="fade" style="animation-delay:1s">'
              + text(40, 622, "Je conçois des sites qui vendent, des marques", "DM5", 26, INK)
              + text(40, 656, "qui fédèrent et des communautés qui reviennent.", "DM5", 26, MUTED)
              + small(W - 40, 652, "Faites défiler", MUTED, "end")
              + f'<g class="bob"><path d="M{W - 40 - small_w("Faites défiler") - 22} 634 v18 m-6 -6 l6 6 l6 -6" stroke="{TOMATO}" stroke-width="2.4" fill="none" stroke-linecap="round"/></g>'
              + "</g>")
    css = ".bob{animation:bob 1.8s ease-in-out infinite}@keyframes bob{50%{transform:translateY(6px)}}"
    defs = (f'<clipPath id="c1"><rect x="0" y="120" width="{W}" height="214"/></clipPath>'
            f'<clipPath id="c2"><rect x="0" y="334" width="{W}" height="236"/></clipPath>')
    stars = "".join(star(x, y, r, c, f' class="wobble" style="animation-delay:{d}s"')
                    for x, y, r, c, d in [(1125, 130, 14, TOMATO, 0), (980, 600, 9, PINK, .8), (1150, 585, 7, BUTTER, 1.6)])
    body = (top + f'<g clip-path="url(#c1)">{l1}</g><g clip-path="url(#c2)">{l2}</g>' + deco + bottom + stars)
    return card(h, body, css, defs)


def marquee():
    h = 230

    def band(items, font, size, gap, y, cls, fill, star_fill, outline=False):
        seq, x = [], 0
        for it in items:
            if outline:
                seq.append(f'<text x="{x:.1f}" y="{y}" font-family="{font}" font-size="{size}" fill="none" '
                           f'stroke="{fill}" stroke-width="1.4">{esc(it)}</text>')
            else:
                seq.append(text(x, y, it, font, size, fill))
            x += F[font].width(it, size) + gap / 2
            seq.append(star(x, y - size * .34, size * .3, star_fill))
            x += gap / 2
        period = x
        reps = math.ceil((W + 400) / period) + 1
        tiles = "".join(f'<g transform="translate({i * period:.1f} 0)">{"".join(seq)}</g>' for i in range(reps))
        return f'<g class="{cls}">{tiles}</g>', period

    t1, p1 = band(["Refontes", "Sites qui vendent", "UX/UI", "Motion", "Marque", "Communauté", "Sur-mesure"],
                  "BG8", 46, 72, 60, "m1", CREAM, BUTTER)
    t2, p2 = band(["Des sites qui vendent", "Des marques qui fédèrent", "Des communautés qui reviennent"],
                  "BG8", 50, 84, 64, "m2", INK, TOMATO, outline=True)
    css = f"""
.m1{{animation:m1 28s linear infinite}}@keyframes m1{{to{{transform:translateX(-{p1:.1f}px)}}}}
.m2{{animation:m2 34s linear infinite;transform:translateX(-{p2:.1f}px)}}@keyframes m2{{to{{transform:translateX(0)}}}}
"""
    body = (f'<g transform="translate(-100 44) rotate(2.2 700 45)"><rect x="0" y="0" width="1500" height="90" fill="{PAPER}" stroke="{LINE}"/>'
            f'{t2}</g>'
            f'<g transform="translate(-100 100) rotate(-2.2 700 45)"><rect x="0" y="0" width="1500" height="86" fill="{TOMATO}"/>'
            f'{t1}</g>')
    return card(h, body, css, bg=None)


def oculot():
    h = 660
    m = mark(44, 118, 300, CREAM, TOMATO, INK)
    size = 150
    t1, e1 = split(372, 258, "Oculot", "BG8", size, -0.045, .15, .06, CREAM)
    t2 = (f'<g class="rise" style="animation-delay:.5s"><text x="372" y="392" font-family="BG8" font-size="{size}" '
          f'letter-spacing="{-0.045 * size:.1f}" fill="none" stroke="{CREAM}" stroke-width="2.2">Studio</text></g>')
    sw = F["BG8"].width("Studio", size, -0.045)
    note = (f'<g class="fade" style="animation-delay:1.1s">'
            + text(372 + sw + 50, 338, "notre studio", "GH", 38, BUTTER)
            + text(372 + sw + 50, 378, "à trois : Tom,", "GH", 38, BUTTER)
            + text(372 + sw + 50, 418, "Eliott et moi", "GH", 38, BUTTER) + "</g>"
            + ring(372 + sw / 2, 348, sw / 2 + 26, 78, BUTTER, 1.3, 4, -3))
    tag = (f'<g class="fade" style="animation-delay:.7s">'
           + text(372, 452, "Studio de refonte de sites internet. Des sites rapides, beaux sur", "DM", 24, "#D9D2C4")
           + text(372, 484, "mobile et pensés pour ramener des clients.", "DM", 24, "#D9D2C4") + "</g>")
    tiles = []
    x = 44
    for i, (lab, fill, fg, dot) in enumerate([("Audit gratuit de votre site", BUTTER, INK, None),
                                              ("Refonte dès 1 500 € HT", PINK, INK, None),
                                              ("PACA · à distance", "none", CREAM, TOMATO)]):
        p, w = pill(x, 540, lab, fill, fg, 13, 46, stroke=(LINE_DARK if fill == "none" else None), dot=dot, delay=.9 + i * .1)
        tiles.append(p)
        x += w + 12
    cta_w = small_w("Parler de votre refonte", 14) + 96
    cta = (f'<g class="fade" style="animation-delay:1.2s">'
           f'<rect x="{W - 44 - cta_w:.1f}" y="536" width="{cta_w:.1f}" height="54" rx="27" fill="{TOMATO}"/>'
           + small(W - 44 - cta_w + 26, 569, "Parler de votre refonte", CREAM, size=14)
           + f'<circle cx="{W - 44 - 27}" cy="563" r="17" fill="{INK}"/>' + arrow(W - 44 - 33, 569, 12, CREAM, 2.2) + "</g>")
    foot = small(44, h - 30, "oculot.studio", CREAM) + small(W - 44, h - 30, "Refontes · Créations · Sur-mesure", "#B8B1A3", "end")
    defs = (f'<clipPath id="o1"><rect x="0" y="100" width="{W}" height="170"/></clipPath>'
            f'<clipPath id="o2"><rect x="0" y="270" width="{W}" height="140"/></clipPath>')
    body = (m + f'<g clip-path="url(#o1)">{t1}</g><g clip-path="url(#o2)">{t2}</g>' + note + tag + "".join(tiles) + cta + foot)
    return card(h, body, "", defs, bg=INK, label=("(01)", "Oculot Studio", "Studio de refonte · Aix-en-Provence"), dark=True)


def nulll():
    h = 640
    name = "NULLL.CLUB"
    size, ls = 168, -0.04
    nw = F["BG8"].width(name, size, ls)
    x0, y0 = (W - nw) / 2, 292
    # parcours qui passe derrière le titre
    route = "M-40 250 C 160 160, 300 360, 520 300 S 820 160, 1000 280 S 1180 380, 1260 300"
    run = (f'<path d="{route}" fill="none" stroke="{TOMATO}" stroke-width="3" stroke-dasharray="4 10" class="flow" opacity=".7"/>'
           f'<circle r="18" fill="{TOMATO}" opacity=".2"><animateMotion dur="8s" repeatCount="indefinite" path="{route}"/></circle>'
           f'<circle r="7" fill="{TOMATO}"><animateMotion dur="8s" repeatCount="indefinite" path="{route}"/></circle>')
    title, _ = split(x0, y0, name, "BG8", size, ls, .1, .05, INK)
    quote = (f'<g class="fade" style="animation-delay:.6s">'
             + text(40, 392, "« On vient pour courir.", "GH", 48, INK)
             + text(40, 444, "On revient pour les gens. »", "GH", 48, TOMATO)
             + text(40, 486, "Fondé et animé par moi : marque, site, réseaux, communauté.", "DM", 20, MUTED)
             + "</g>")
    sticker = (f'<g class="fade" style="animation-delay:.8s" transform="rotate(-8 1040 420)">'
               f'<rect x="930" y="384" width="220" height="72" rx="36" fill="{BUTTER}"/>'
               + text(1040, 430, "chaque samedi", "GH", 32, INK, "middle") + "</g>")
    stats = [("Quand", "Samedi 8h30"), ("Distance", "5 à 6 km"), ("Prix", "Gratuit"), ("Allure", "Conversation")]
    cw = 1120 / 4
    st = [f'<line x1="40" y1="522" x2="{W - 40}" y2="522" stroke="{LINE}"/>']
    for i, (k, v) in enumerate(stats):
        x = 40 + i * cw
        if i:
            st.append(f'<line x1="{x:.1f}" y1="522" x2="{x:.1f}" y2="{h - 30}" stroke="{LINE}"/>')
        st.append(f'<g class="fade" style="animation-delay:{.9 + i * .1:.2f}s">'
                  + small(x + (18 if i else 0), 556, k)
                  + text(x + (18 if i else 0), 598, v, "BG7", 32, INK, ls=-0.02) + "</g>")
    css = ".flow{animation:flow 1.2s linear infinite}@keyframes flow{to{stroke-dashoffset:-28}}"
    defs = f'<clipPath id="n1"><rect x="0" y="120" width="{W}" height="200"/></clipPath>'
    body = run + f'<g clip-path="url(#n1)">{title}</g>' + quote + sticker + "".join(st)
    return card(h, body, css, defs, bg=PAPER, label=("(02)", "NULLL.CLUB", "Social running club · Aix-en-Provence"))


def services():
    rows = [
        ("Sites & refontes", "Vitrine · Refonte · SEO"),
        ("UX/UI & motion", "Parcours · Micro-interactions"),
        ("Logiciels sur mesure", "Espace client · Outils · ERP"),
        ("Marque & communauté", "Identité · Contenu · Réseaux"),
        ("Automatisations & IA", "Prototypage · Outils internes"),
    ]
    top, rh = 96, 90
    h = top + rh * len(rows) + 40
    out = []
    for i, (t, tags) in enumerate(rows):
        y0 = top + i * rh
        out.append(f'<g class="fade" style="animation-delay:{.1 + i * .1:.2f}s">'
                   + small(40, y0 + 56, f"0{i + 1}", TOMATO, size=14)
                   + text(120, y0 + 62, t, "BG8", 46, INK, ls=-0.03)
                   + small(W - 100, y0 + 56, tags, MUTED, "end")
                   + arrow(W - 68, y0 + 62, 20, INK) + "</g>")
        out.append(f'<line class="draw" style="animation-delay:{.2 + i * .1:.2f}s" x1="40" y1="{y0 + rh}" '
                   f'x2="{W - 40}" y2="{y0 + rh}" stroke="{LINE}" pathLength="1"/>')
    n = len(rows)
    stops = "".join(f"{i / n * 100 + 2:.1f}%,{(i + 1) / n * 100 - 2:.1f}%{{transform:translateY({i * rh}px)}}" for i in range(n))
    css = f".hl{{mix-blend-mode:multiply;animation:hl {n * 2.2:.1f}s cubic-bezier(.7,0,.2,1) infinite}}@keyframes hl{{{stops}}}"
    hl = f'<rect class="hl" x="24" y="{top + 6}" width="{W - 48}" height="{rh - 12}" rx="16" fill="{BUTTER}"/>'
    return card(h, hl + "".join(out), css, bg=PAPER, label=("(03)", "Services", "Ce que je fais"))


def opensource():
    h = 320
    p, pw = pill(40, 100, "Plugin Claude Code · gratuit", TOMATO, CREAM, 12, 36, delay=.1)
    title = f'<g class="fade" style="animation-delay:.2s">{text(40, 212, "ovh-dns", "BG8", 78, INK, ls=-0.04)}</g>'
    sub = (f'<g class="fade" style="animation-delay:.35s">'
           + text(40, 252, "Pointez un domaine OVH vers Vercel en trois commandes,", "DM", 21, INK)
           + text(40, 280, "sans jamais casser vos e-mails.", "DM", 21, MUTED) + "</g>")
    tx, ty, tw = 640, 104, 520
    cmds = ["/plugin marketplace add tbsrgt/claude-ovh-dns", "/plugin install ovh-dns@tbsrgt"]
    term = (f'<g class="fade" style="animation-delay:.5s">'
            f'<rect x="{tx}" y="{ty}" width="{tw}" height="150" rx="18" fill="{INK}"/>'
            f'<circle cx="{tx + 24}" cy="{ty + 24}" r="5" fill="{TOMATO}"/><circle cx="{tx + 42}" cy="{ty + 24}" r="5" fill="{BUTTER}"/>'
            f'<circle cx="{tx + 60}" cy="{ty + 24}" r="5" fill="{PINK}"/>'
            + "".join(text(tx + 24, ty + 72 + i * 36, c, "JB", 15.5, CREAM) for i, c in enumerate(cmds))
            + f'<rect class="pulse" x="{tx + 24 + F["JB"].width(cmds[-1], 15.5) + 6:.1f}" y="{ty + 72 + 36 - 14}" width="9" height="18" fill="{TOMATO}"/>'
            + "</g>")
    foot = small(640, 290, "github.com/tbsrgt/claude-ovh-dns", MUTED) + small(W - 40, 290, "MIT · Python", MUTED, "end")
    return card(h, p + title + sub + term + foot, bg=CREAM, label=("(04)", "Open source", "Mes outils, en libre accès"))


def stack():
    h = 200
    tools = ["Next.js", "React", "TypeScript", "CSS Modules", "Motion", "Lenis", "Supabase",
             "Vercel", "Figma", "Remotion", "Python", "Playwright"]
    seq, x = [], 0
    for t in tools:
        w = small_w(t, 14) + 50
        seq.append(f'<rect x="{x:.1f}" y="110" width="{w:.1f}" height="52" rx="26" fill="{PAPER}" stroke="{LINE}"/>'
                   + star(x + 24, 136, 7, TOMATO)
                   + small(x + w / 2 + 10, 141, t, INK, "middle", 14))
        x += w + 14
    period = x
    tiles = "".join(f'<g transform="translate({40 + i * period:.1f} 0)">{"".join(seq)}</g>' for i in range(3))
    css = f".mq{{animation:mq 32s linear infinite}}@keyframes mq{{to{{transform:translateX(-{period:.1f}px)}}}}"
    defs = ('<linearGradient id="edge"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            '<stop offset=".1" stop-color="#fff"/><stop offset=".9" stop-color="#fff"/>'
            '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            f'<mask id="edges"><rect width="{W}" height="{h}" fill="url(#edge)"/></mask>')
    return card(h, f'<g mask="url(#edges)"><g class="mq">{tiles}</g></g>', css, defs,
                label=("(05)", "Outils", "Stack du moment"))


def contact():
    h = 480
    size = 156
    w1 = F["BG8"].width("Parlons-", size, -0.045)
    big = (f'<g clip-path="url(#cl)">'
           f'<g class="rise" style="animation-delay:.1s">{text(34, 290, "Parlons-", "BG8", size, INK, ls=-0.045)}</g>'
           f'<g class="rise" style="animation-delay:.25s">{text(34 + w1, 290, "en.", "BG8", size, TOMATO, ls=-0.045)}</g>'
           "</g>" + underline(40 + w1, 40 + w1 + F["BG8"].width("en.", size, -0.045) - 12, 312, BUTTER, .9, 8))
    sub = (f'<g class="fade" style="animation-delay:.5s">'
           + text(40, 360, "Un site, une refonte, une marque à lancer ? Écrivez-nous.", "DM5", 24, MUTED) + "</g>")
    bd = f'<g class="fade" style="animation-delay:.4s">{badge(1030, 232, 82, "Disponible • Pour nouveaux projets • 2026 • ", BUTTER, INK, TOMATO)}</g>'
    foot = (f'<line x1="40" y1="{h - 76}" x2="{W - 40}" y2="{h - 76}" stroke="{LINE}"/>'
            + small(40, h - 40, "bonjour@oculot.studio", INK)
            + small(W / 2, h - 40, "Aix-en-Provence · FR / EN", MUTED, "middle")
            + small(W - 40, h - 40, "© 2026 Tobias Ringot", MUTED, "end"))
    defs = f'<clipPath id="cl"><rect x="0" y="120" width="{W}" height="200"/></clipPath>'
    return card(h, big + sub + bd + foot, "", defs, bg=CREAM, label=("(06)", "Contact", "Écrivez-nous"))


def button(label, kind="ghost"):
    size = 13
    tw = small_w(label, size)
    w, h = tw + 72, 46
    fill, fg, stroke = {
        "primary": (TOMATO, CREAM, TOMATO),
        "dark": (INK, CREAM, INK),
        "butter": (BUTTER, INK, BUTTER),
        "ghost": (PAPER, INK, "#15130F33"),
    }[kind]
    body = (f'<rect x=".5" y=".5" width="{w - 1:.1f}" height="{h - 1}" rx="23" fill="{fill}" stroke="{stroke}"/>'
            + small(24, 28, label, fg, size=size)
            + arrow(w - 38, 29, 12, fg, 1.8))
    face = F["DM6"].face(label.upper())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.1f} {h}" width="{w:.1f}" height="{h}">'
            f'<style>{face}</style>{body}</svg>\n')


BUTTONS = {
    "btn-contact": ("Me contacter", "primary"),
    "btn-oculot": ("Oculot Studio", "dark"),
    "btn-nulll": ("NULLL.CLUB", "butter"),
    "btn-portfolio": ("Portfolio", "ghost"),
    "btn-linkedin": ("LinkedIn", "ghost"),
    "btn-instagram": ("Instagram", "ghost"),
    "btn-behance": ("Behance", "ghost"),
}


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    cards = {"hero": hero, "marquee": marquee, "oculot": oculot, "nulll": nulll, "services": services,
             "opensource": opensource, "stack": stack, "contact": contact}
    for name, fn in cards.items():
        (OUT / f"{name}.svg").write_text(fn())
    for name, (label, kind) in BUTTONS.items():
        (OUT / f"{name}.svg").write_text(button(label, kind))
    for p in sorted(OUT.glob("*.svg")):
        print(f"{p.name:22} {p.stat().st_size / 1024:6.1f} Ko")


if __name__ == "__main__":
    main()
