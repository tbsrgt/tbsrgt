"""Génère les cartes SVG animées du README de profil.

    python3 -m venv .venv && .venv/bin/pip install fonttools brotli
    .venv/bin/python _build/build.py

Les polices (OFL, Google Fonts) sont téléchargées dans _build/fonts puis
sous-ensemblées et intégrées en base64 dans chaque SVG : GitHub affiche les
SVG comme des images, sans accès aux polices externes ni au JavaScript. Les
effets (aurora, split text, shiny text, marquee, glitch, circular text)
sont donc refaits en CSS/SMIL.
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
    "SpaceGrotesk.ttf": f"{GF}/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",
    "InstrumentSerif-Italic.ttf": f"{GF}/instrumentserif/InstrumentSerif-Italic.ttf",
    "JetBrainsMono.ttf": f"{GF}/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
    "InterTight.ttf": f"{GF}/intertight/InterTight%5Bwght%5D.ttf",
}

W = 1200
BG = "#0B0B0B"
FG = "#F2F0EB"
MUTED = "#8C8A84"
LINE = "#FFFFFF1F"
LIME = "#C6FF3D"


# ---------------------------------------------------------------- fonts

class Font:
    def __init__(self, family, file, wght=None):
        self.family = family
        self.tt = TTFont(FONT_DIR / file)
        if wght is not None:
            self.tt = instantiateVariableFont(self.tt, {"wght": wght})
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
        "SG7": Font("SG7", "SpaceGrotesk.ttf", 700),
        "SG5": Font("SG5", "SpaceGrotesk.ttf", 500),
        "IS": Font("IS", "InstrumentSerif-Italic.ttf"),
        "JB": Font("JB", "JetBrainsMono.ttf", 500),
        "IT": Font("IT", "InterTight.ttf", 400),
        "IT5": Font("IT5", "InterTight.ttf", 500),
    }


F = load_fonts()


# ---------------------------------------------------------------- helpers

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, font, size, fill=FG, anchor="start", ls=0.0, extra=""):
    ls_attr = f' letter-spacing="{ls * size:.2f}"' if ls else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}"{ls_attr} {extra}>{esc(s)}</text>')


def mono(x, y, s, fill=MUTED, anchor="start", size=13):
    return text(x, y, s.upper(), "JB", size, fill, anchor, 0.08)


BASE_CSS = """
.fade{animation:fade 1s cubic-bezier(.2,.8,.2,1) both}
@keyframes fade{from{opacity:0;transform:translateY(24px)}}
.rise{animation:rise 1.1s cubic-bezier(.2,.8,.2,1) both}
@keyframes rise{from{transform:translateY(260px)}}
.pulse{animation:pulse 1.6s ease-in-out infinite}
@keyframes pulse{50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def grain(id_="grain", opacity=0.07, h=800):
    return (f'<filter id="{id_}"><feTurbulence type="fractalNoise" baseFrequency=".85" '
            f'numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  '
            f'0 0 0 0 1  0 0 0 .9 0"/></filter>'
            f'<rect width="{W}" height="{h}" filter="url(#{id_})" opacity="{opacity}"/>')


def card(h, body, css="", defs="", bg=True, label=None):
    """Carte arrondie sombre, polices intégrées pour tout le texte utilisé."""
    head = ""
    if label:
        num, title, right = label
        head = (mono(40, 52, num, LIME) + mono(96, 52, title, FG) + mono(W - 40, 52, right, MUTED, "end")
                + f'<line x1="40" y1="74" x2="{W - 40}" y2="74" stroke="{LINE}"/>')
    inner = head + body
    used = set(f for f in F if f'font-family="{f}"' in inner)
    faces = "".join(F[f].face("".join(sorted(set(inner)))) for f in used)
    back = (f'<rect width="{W}" height="{h}" fill="{BG}"/>' + grain(h=h)) if bg else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}">
<style>{faces}{BASE_CSS}{css}</style>
<defs><clipPath id="round"><rect width="{W}" height="{h}" rx="{28 if bg else 0}"/></clipPath>{defs}</defs>
<g clip-path="url(#round)">{back}{inner}</g>
</svg>
'''


def split(x, y, word, font, size, ls, delay0, step, fill):
    """SplitText : chaque lettre monte depuis un masque, en décalé."""
    out, cx = [], x
    for i, ch in enumerate(word):
        out.append(f'<g class="rise" style="animation-delay:{delay0 + i * step:.2f}s">'
                   + text(cx, y, ch, font, size, fill) + "</g>")
        cx += F[font].width(ch, size, ls)
    return "".join(out), cx


def star(cx, cy, r, fill):
    pts = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.28
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{fill}"/>'


def arrow(x, y, s, color, sw=2):
    """Flèche ↗ dessinée (x,y = coin bas-gauche)."""
    return (f'<path d="M{x} {y} L{x + s} {y - s} M{x + s * .3} {y - s} H{x + s} V{y - s * .7}" '
            f'stroke="{color}" stroke-width="{sw}" fill="none" stroke-linecap="square"/>')


# ---------------------------------------------------------------- cards

def hero():
    h = 700
    cols = "".join(f'<line x1="{40 + i * 1120 / 6:.1f}" y1="0" x2="{40 + i * 1120 / 6:.1f}" y2="{h}" stroke="#FFFFFF0D"/>'
                   for i in range(7))
    aurora = f'''<g filter="url(#blur)" opacity=".6">
<ellipse class="a1" cx="260" cy="640" rx="420" ry="170" fill="#4B2BFF"/>
<ellipse class="a2" cx="760" cy="700" rx="460" ry="160" fill="#FF4F8B"/>
<ellipse class="a3" cx="1080" cy="560" rx="280" ry="150" fill="{LIME}" opacity=".55"/></g>'''
    top = (mono(40, 58, "Tobias Ringot ©2026", FG) + mono(40 + 1120 / 3, 58, "Web designer & développeur")
           + mono(40 + 2240 / 3, 58, "Aix-en-Provence, FR")
           + mono(W - 40, 58, "Dispo pour projets", FG, "end")
           + f'<circle class="pulse" cx="{W - 40 - F["JB"].width("DISPO POUR PROJETS", 13, .08) - 14:.1f}" cy="53.5" r="4.5" fill="{LIME}"/>'
           + f'<line x1="40" y1="82" x2="{W - 40}" y2="82" stroke="{LINE}"/>')
    l1, end1 = split(30, 330, "Tobias", "SG7", 215, -0.055, .15, .06, FG)
    l2, _ = split(300, 540, "Ringot", "IS", 250, -0.02, .45, .06, "url(#shine)")
    side = (mono(end1 + 36, 200, "(Web · Marque", MUTED) + mono(end1 + 36, 222, "· Communauté · IA)", MUTED))
    left_note = (mono(40, 420, "(01)", LIME) + mono(40, 442, "Designer") + mono(40, 464, "Développeur")
                 + mono(40, 486, "Community builder"))
    bottom = (f'<g class="fade" style="animation-delay:1s">'
              + text(40, 628, "Je conçois des sites qui vendent, des marques", "IT", 24, FG)
              + text(40, 660, "qui fédèrent et des communautés qui reviennent.", "IT", 24, MUTED)
              + mono(W - 40, 660, "Scroll", MUTED, "end")
              + f'<g class="bob"><path d="M{W - 112} 640 v22 m-7 -7 l7 7 l7 -7" stroke="{LIME}" stroke-width="2" fill="none"/></g>'
              + "</g>")
    css = """
.a1{animation:d1 16s ease-in-out infinite alternate}.a2{animation:d2 20s ease-in-out infinite alternate}
.a3{animation:d3 13s ease-in-out infinite alternate}
@keyframes d1{to{transform:translate(260px,-90px)}}@keyframes d2{to{transform:translate(-300px,-60px)}}
@keyframes d3{to{transform:translate(-220px,70px)}}
.bob{animation:bob 1.8s ease-in-out infinite}@keyframes bob{50%{transform:translateY(6px)}}
"""
    defs = f'''<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="90"/></filter>
<clipPath id="c1"><rect x="0" y="160" width="{W}" height="200"/></clipPath>
<clipPath id="c2"><rect x="0" y="365" width="{W}" height="240"/></clipPath>
<linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="-700" y1="0" x2="-100" y2="0">
<stop offset="0" stop-color="{LIME}"/><stop offset=".42" stop-color="{LIME}"/><stop offset=".5" stop-color="#FFFFFF"/>
<stop offset=".58" stop-color="{LIME}"/><stop offset="1" stop-color="{LIME}"/>
<animate attributeName="x1" values="-700;1300" dur="4.5s" repeatCount="indefinite"/>
<animate attributeName="x2" values="-100;1900" dur="4.5s" repeatCount="indefinite"/></linearGradient>'''
    body = (aurora + cols + top + f'<g clip-path="url(#c1)">{l1}</g><g clip-path="url(#c2)">{l2}</g>'
            + f'<g class="fade" style="animation-delay:.9s">{side}{left_note}</g>' + bottom)
    return card(h, body, css, defs)


def marquee():
    h = 230

    def band(items, font, size, gap, y, cls, fill, outline=False):
        seq, x = [], 0
        for it in items:
            if outline:
                seq.append(f'<text x="{x:.1f}" y="{y}" font-family="{font}" font-size="{size}" fill="none" '
                           f'stroke="{fill}" stroke-width="1.2">{esc(it)}</text>')
            else:
                seq.append(text(x, y, it, font, size, fill))
            x += F[font].width(it, size) + gap / 2
            seq.append(star(x, y - size * .36, size * .28, LIME if outline else BG))
            x += gap / 2
        period = x
        reps = math.ceil((W + 400) / period) + 1
        tiles = "".join(f'<g transform="translate({i * period:.1f} 0)">{"".join(seq)}</g>' for i in range(reps))
        return f'<g class="{cls}" style="--p:-{period:.1f}px">{tiles}</g>', period

    t1, p1 = band(["Web design", "Refontes", "UX/UI", "Motion", "Branding", "Community building", "IA"],
                  "SG7", 44, 70, 60, "m1", BG)
    t2, p2 = band(["Des sites qui vendent", "Des marques qui fédèrent", "Des communautés qui reviennent"],
                  "IS", 52, 80, 66, "m2", FG, outline=True)
    css = f"""
.m1{{animation:m1 28s linear infinite}}@keyframes m1{{to{{transform:translateX(-{p1:.1f}px)}}}}
.m2{{animation:m2 34s linear infinite;transform:translateX(-{p2:.1f}px)}}@keyframes m2{{to{{transform:translateX(0)}}}}
"""
    body = (f'<g transform="translate(-100 44) rotate(2.2 700 45)"><rect x="0" y="0" width="1500" height="90" fill="{BG}"/>'
            f'<g transform="translate(0 0)">{t2}</g></g>'
            f'<g transform="translate(-100 100) rotate(-2.2 700 45)"><rect x="0" y="0" width="1500" height="84" fill="{LIME}"/>'
            f'{t1}</g>')
    return card(h, body, css, bg=False)


def about():
    h = 580
    L = [
        [("Je conçois des sites qui ont du ", "IT5"), ("caractère", "IS")],
        [("— refontes complètes, UX/UI, design,", "IT5")],
        [("animations — en mêlant marketing digital,", "IT5")],
        [("création de marque, communauté et ", "IT5"), ("IA.", "IS")],
    ]
    lines = []
    for i, runs in enumerate(L):
        spans = "".join(
            f'<tspan font-family="{f}" fill="{LIME if f == "IS" else FG}" '
            f'font-size="{58 if f == "IS" else 50}">{esc(s)}</tspan>' for s, f in runs)
        y = 170 + i * 66
        lines.append(f'<g class="fade" style="animation-delay:{.15 + i * .12:.2f}s">'
                     f'<text x="40" y="{y}" letter-spacing="-1">{spans}</text></g>')
    # formule en pastilles
    items = ["Marketing digital", "Marque", "Community", "Web design / dev", "IA"]
    x, y, pills = 40, 498, []
    for i, it in enumerate(items):
        w = F["JB"].width(it.upper(), 14, .08) + 40
        last = i == len(items) - 1
        pills.append(f'<g class="fade" style="animation-delay:{.8 + i * .1:.2f}s">'
                     f'<rect x="{x}" y="{y - 30}" width="{w:.1f}" height="46" rx="23" '
                     f'fill="{LIME if last else "none"}" stroke="{LIME if last else "#FFFFFF40"}"/>'
                     + text(x + w / 2, y - 1, it.upper(), "JB", 14, BG if last else FG, "middle", .08) + "</g>")
        x += w
        if not last:
            pills.append(text(x + 22, y + 3, "+", "SG5", 28, LIME, "middle"))
            x += 44
    note = mono(40, 430, "La formule —", MUTED)
    body = "".join(lines) + note + "".join(pills)
    return card(h, body, label=("(01)", "À propos", "Qui suis-je ?"))


def services():
    rows = [
        ("Sites & refontes", "Vitrine · Refonte · SEO"),
        ("UX/UI & motion", "Parcours · Micro-interactions"),
        ("Logiciels sur mesure", "Espace client · Outils · ERP"),
        ("Marque & communauté", "Identité · Contenu · Réseaux"),
        ("Développement boosté à l'IA", "Prototypage · Automatisation"),
    ]
    top, rh = 96, 92
    h = top + rh * len(rows) + 40
    out = []
    for i, (t, tags) in enumerate(rows):
        y0 = top + i * rh
        out.append(f'<g class="fade" style="animation-delay:{.1 + i * .1:.2f}s">'
                   + mono(40, y0 + 56, f"0{i + 1}", MUTED, size=14)
                   + text(130, y0 + 62, t, "SG5", 46, FG, ls=-0.02)
                   + mono(W - 100, y0 + 56, tags, MUTED, "end")
                   + arrow(W - 68, y0 + 62, 20, FG) + "</g>")
        out.append(f'<line class="draw" style="animation-delay:{.2 + i * .1:.2f}s" x1="40" y1="{y0 + rh}" '
                   f'x2="{W - 40}" y2="{y0 + rh}" stroke="{LINE}" pathLength="1"/>')
    n = len(rows)
    stops = []
    for i in range(n):
        a, b = i / n * 100, (i + 1) / n * 100
        stops.append(f"{a + 2:.1f}%,{b - 2:.1f}%{{transform:translateY({i * rh}px)}}")
    css = f"""
.draw{{stroke-dasharray:1;animation:draw 1.2s cubic-bezier(.6,0,.2,1) both}}@keyframes draw{{from{{stroke-dashoffset:1}}}}
.hl{{mix-blend-mode:difference;animation:hl {n * 2.2:.1f}s cubic-bezier(.7,0,.2,1) infinite}}
@keyframes hl{{{"".join(stops)}}}
"""
    hl = f'<rect class="hl" x="24" y="{top + 4}" width="{W - 48}" height="{rh - 8}" rx="14" fill="{FG}"/>'
    return card(h, "".join(out) + hl, css, label=("(02)", "Services", "Ce que je fais"))


def nulll():
    h = 640
    name = "NULLL.CLUB"
    size, ls = 172, -0.04
    nw = F["SG7"].width(name, size, ls)
    x0, y0 = (W - nw) / 2, 290

    def layer(fill, dx, cid, extra=""):
        return (f'<g clip-path="url(#{cid})" style="mix-blend-mode:screen">'
                f'<g>{text(x0, y0, name, "SG7", size, fill, ls=ls)}'
                f'<animateTransform attributeName="transform" type="translate" calcMode="discrete" '
                f'values="0 0;{dx} 0;{-dx / 2} 0;{dx * 1.5} 0;0 0" keyTimes="0;.86;.9;.94;.98" dur="3.2s" '
                f'repeatCount="indefinite"{extra}/></g></g>')

    def clip(cid, seq):
        vals = ";".join(f"{a}" for a, _ in seq)
        hs = ";".join(f"{b}" for _, b in seq)
        return (f'<clipPath id="{cid}"><rect x="0" width="{W}" y="0" height="0">'
                f'<animate attributeName="y" calcMode="discrete" values="{vals}" keyTimes="0;.86;.9;.94;.98" dur="3.2s" repeatCount="indefinite"/>'
                f'<animate attributeName="height" calcMode="discrete" values="{hs}" keyTimes="0;.86;.9;.94;.98" dur="3.2s" repeatCount="indefinite"/>'
                f'</rect></clipPath>')

    defs = (clip("g1", [(0, 0), (170, 40), (230, 30), (150, 70), (0, 0)])
            + clip("g2", [(0, 0), (240, 30), (160, 50), (210, 60), (0, 0)]))
    title = (f'<g class="fade" style="animation-delay:.1s">' + text(x0, y0, name, "SG7", size, FG, ls=ls)
             + layer("#FF2E4D", 8, "g1") + layer("#00E0FF", -8, "g2") + "</g>")
    quote = (f'<g class="fade" style="animation-delay:.4s">'
             + text(40, 396, "« On vient pour courir.", "IS", 46, FG)
             + text(40, 446, "On revient pour les gens. »", "IS", 46, LIME)
             + mono(40, 486, "Fondé & animé par moi : marque, site, réseaux, communauté.")
             + "</g>")
    route = "M760 430 C 760 360, 860 330, 930 350 S 1060 420, 1120 380 S 1170 300, 1090 320 S 980 470, 880 460 S 760 480, 760 430 Z"
    run = (f'<g class="fade" style="animation-delay:.6s">'
           f'<path d="{route}" fill="none" stroke="#FFFFFF33" stroke-width="2" stroke-dasharray="3 7" class="flow"/>'
           f'<circle r="16" fill="{LIME}" opacity=".18"><animateMotion dur="7s" repeatCount="indefinite" path="{route}"/></circle>'
           f'<circle r="6" fill="{LIME}"><animateMotion dur="7s" repeatCount="indefinite" path="{route}"/></circle>'
           f'<circle cx="760" cy="430" r="4" fill="{FG}"/>' + mono(772, 470, "Départ 8:30", FG, size=11) + "</g>")
    stats = [("Quand", "Samedi 8h30"), ("Distance", "5–6 km"), ("Prix", "Gratuit"), ("Allure", "Conversation")]
    sw = 1120 / 4
    st = [f'<line x1="40" y1="522" x2="{W - 40}" y2="522" stroke="{LINE}"/>']
    for i, (k, v) in enumerate(stats):
        x = 40 + i * sw
        if i:
            st.append(f'<line x1="{x:.1f}" y1="522" x2="{x:.1f}" y2="{h - 30}" stroke="{LINE}"/>')
        st.append(f'<g class="fade" style="animation-delay:{.7 + i * .1:.2f}s">'
                  + mono(x + (18 if i else 0), 556, k) + text(x + (18 if i else 0), 598, v, "SG5", 32, FG, ls=-0.02) + "</g>")
    css = ".flow{animation:flow 1.2s linear infinite}@keyframes flow{to{stroke-dashoffset:-20}}"
    return card(h, title + quote + run + "".join(st), css, defs,
                label=("(03)", "Side project", "Social running club — Aix-en-Provence"))


def stack():
    h = 200
    tools = ["Next.js", "React", "TypeScript", "Tailwind CSS", "Motion", "Lenis", "Supabase",
             "Vercel", "Figma", "Claude", "Python"]
    seq, x = [], 0
    for t in tools:
        w = F["JB"].width(t.upper(), 15, .08) + 48
        seq.append(f'<rect x="{x:.1f}" y="110" width="{w:.1f}" height="52" rx="26" fill="none" stroke="#FFFFFF33"/>'
                   + f'<circle cx="{x + 22:.1f}" cy="136" r="3.5" fill="{LIME}"/>'
                   + text(x + w / 2 + 8, 141, t.upper(), "JB", 15, FG, "middle", .08))
        x += w + 14
    period = x
    tiles = "".join(f'<g transform="translate({40 + i * period:.1f} 0)">{"".join(seq)}</g>' for i in range(3))
    css = f".mq{{animation:mq 30s linear infinite}}@keyframes mq{{to{{transform:translateX(-{period:.1f}px)}}}}"
    defs = ('<linearGradient id="edge"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            '<stop offset=".12" stop-color="#fff"/><stop offset=".88" stop-color="#fff"/>'
            '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            f'<mask id="edges"><rect width="{W}" height="{h}" fill="url(#edge)"/></mask>')
    return card(h, f'<g mask="url(#edges)"><g class="mq">{tiles}</g></g>', css, defs,
                label=("(04)", "Outils", "Stack du moment"))


def contact():
    h = 470
    cx, cy, r = 1010, 250, 92
    ring = "Disponible • Pour nouveaux projets • 2026 • "
    circ = 2 * math.pi * r
    big = (f'<g clip-path="url(#cl)">'
           f'<g class="rise" style="animation-delay:.1s">{text(34, 290, "Parlons-", "SG7", 160, FG, ls=-0.05)}</g>'
           f'<g class="rise" style="animation-delay:.25s">{text(40 + F["SG7"].width("Parlons-", 160, -0.05), 290, "en.", "IS", 180, "url(#shine)")}</g>'
           "</g>")
    sub = (f'<g class="fade" style="animation-delay:.5s">'
           + text(40, 352, "Un site, une refonte, une marque à lancer ? Écris-moi.", "IT", 24, MUTED) + "</g>")
    badge = (f'<g class="spin"><path id="ring" d="M{cx - r} {cy} a{r} {r} 0 1 1 {2 * r} 0 a{r} {r} 0 1 1 {-2 * r} 0" fill="none"/>'
             f'<text font-family="JB" font-size="13" fill="{FG}" textLength="{circ - 4:.1f}" lengthAdjust="spacing">'
             f'<textPath href="#ring">{esc(ring.upper())}</textPath></text></g>'
             f'<circle cx="{cx}" cy="{cy}" r="{r - 26}" fill="{LIME}"/>' + arrow(cx - 18, cy + 18, 36, BG, 3.5))
    foot = (f'<line x1="40" y1="{h - 76}" x2="{W - 40}" y2="{h - 76}" stroke="{LINE}"/>'
            + mono(40, h - 40, "tobiasringot13@gmail.com", FG)
            + mono(W / 2, h - 40, "Aix-en-Provence — FR / EN", MUTED, "middle")
            + mono(W - 40, h - 40, "© 2026 Tobias Ringot", MUTED, "end"))
    css = f".spin{{transform-origin:{cx}px {cy}px;animation:spin 16s linear infinite}}@keyframes spin{{to{{transform:rotate(360deg)}}}}"
    defs = f'''<clipPath id="cl"><rect x="0" y="120" width="{W}" height="200"/></clipPath>
<linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="-700" y1="0" x2="-100" y2="0">
<stop offset="0" stop-color="{LIME}"/><stop offset=".42" stop-color="{LIME}"/><stop offset=".5" stop-color="#FFFFFF"/>
<stop offset=".58" stop-color="{LIME}"/><stop offset="1" stop-color="{LIME}"/>
<animate attributeName="x1" values="-700;1300" dur="4.5s" repeatCount="indefinite"/>
<animate attributeName="x2" values="-100;1900" dur="4.5s" repeatCount="indefinite"/></linearGradient>'''
    return card(h, big + sub + badge + foot, css, defs, label=("(05)", "Contact", "Écris-moi"))


def button(label, primary=False):
    size = 13
    tw = F["JB"].width(label.upper(), size, .08)
    w, h = tw + 72, 46
    fill, fg = (LIME, BG) if primary else (BG, FG)
    stroke = LIME if primary else "#FFFFFF3A"
    body = (f'<rect x=".5" y=".5" width="{w - 1:.1f}" height="{h - 1}" rx="23" fill="{fill}" stroke="{stroke}"/>'
            + text(24, 28, label.upper(), "JB", size, fg, ls=.08)
            + arrow(w - 38, 29, 12, LIME if not primary else BG, 1.8))
    face = F["JB"].face(label.upper())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.1f} {h}" width="{w:.1f}" height="{h}">'
            f'<style>{face}</style>{body}</svg>\n')


BUTTONS = {
    "btn-contact": ("Me contacter", True),
    "btn-portfolio": ("Portfolio", False),
    "btn-linkedin": ("LinkedIn", False),
    "btn-instagram": ("Instagram", False),
    "btn-nulll": ("NULLL.CLUB", False),
    "btn-behance": ("Behance", False),
}


def main():
    OUT.mkdir(exist_ok=True)
    cards = {"hero": hero, "marquee": marquee, "about": about, "services": services,
             "nulll": nulll, "stack": stack, "contact": contact}
    for name, fn in cards.items():
        (OUT / f"{name}.svg").write_text(fn())
    for name, (label, primary) in BUTTONS.items():
        (OUT / f"{name}.svg").write_text(button(label, primary))
    for p in sorted(OUT.glob("*.svg")):
        print(f"{p.name:22} {p.stat().st_size / 1024:6.1f} Ko")


if __name__ == "__main__":
    main()
