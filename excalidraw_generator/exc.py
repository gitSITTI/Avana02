"""Tiny Excalidraw scene builder. Produces valid .excalidraw JSON with frames, bound text and bound arrows."""
import json, random, textwrap

INK = '#1e1e1e'
CW = {1: 0.60, 2: 0.55, 3: 0.60, 5: 0.58}  # average char width / font size by family
LH = 1.25


class Doc:
    def __init__(self, seed=7):
        self.els = []
        self.n = 0
        self.rng = random.Random(seed)
        self.frame = None
        self.frame_kids = []

    # ---------- core ----------
    def nid(self):
        self.n += 1
        return 'e%05d' % self.n

    def base(self, typ, x, y, w, h, stroke=INK, bg='transparent', sw=1, style='solid', rough=0, opacity=100, fill='solid', rnd=None):
        return dict(
            id=self.nid(), type=typ, x=x, y=y, width=w, height=h, angle=0, strokeColor=stroke, backgroundColor=bg,
            fillStyle=fill, strokeWidth=sw, strokeStyle=style, roughness=rough, opacity=opacity, groupIds=[],
            frameId=self.frame['id'] if self.frame else None, roundness=rnd, seed=self.rng.randint(1, 2**31 - 1),
            version=1, versionNonce=self.rng.randint(1, 2**31 - 1), isDeleted=False, boundElements=None,
            updated=1760000000000, link=None, locked=False)

    def add(self, e):
        self.els.append(e)
        if self.frame:
            self.frame_kids.append(e)
        return e

    # ---------- text ----------
    def text(self, x, y, s, fs=14, color=INK, align='left', family=2, w=None, container=None, valign='top'):
        lines = s.split('\n')
        tw = max(len(l) for l in lines) * fs * CW.get(family, 0.55)
        width = w if w is not None else tw
        e = self.base('text', x, y, width, len(lines) * fs * LH, stroke=color)
        e.update(text=s, fontSize=fs, fontFamily=family, textAlign=align, verticalAlign=valign, containerId=container,
                 originalText=s, autoResize=(w is None), lineHeight=LH)
        return self.add(e)

    def wrap(self, s, width_px, fs, family=2):
        maxc = max(1, int(width_px / (fs * CW.get(family, 0.55))))
        out = []
        for para in s.split('\n'):
            out += textwrap.wrap(para, maxc) or ['']
        return '\n'.join(out)

    def _label(self, shape, label, fs, color, align, valign, family, pad):
        x, y, w, h = shape['x'], shape['y'], shape['width'], shape['height']
        s = self.wrap(label, w - 2 * pad, fs, family)
        th = (s.count('\n') + 1) * fs * LH
        ty = y + (h - th) / 2 if valign == 'middle' else y + pad
        t = self.text(x + pad, ty, s, fs=fs, color=color, align=align, family=family, w=w - 2 * pad, container=shape['id'], valign=valign)
        t['height'] = th
        shape['boundElements'] = (shape['boundElements'] or []) + [{'id': t['id'], 'type': 'text'}]
        return t

    # ---------- shapes ----------
    def shape(self, typ, x, y, w, h, label=None, fs=13, fill='transparent', stroke=INK, sw=1, dash=False, rough=0,
              rounded=True, color=INK, align='center', valign='middle', family=2, pad=6, opacity=100):
        rnd = {'type': 3} if (rounded and typ == 'rectangle') else ({'type': 2} if typ in ('ellipse', 'diamond') else None)
        e = self.base(typ, x, y, w, h, stroke=stroke, bg=fill, sw=sw, style='dashed' if dash else 'solid', rough=rough, opacity=opacity, rnd=rnd)
        self.add(e)
        if label:
            self._label(e, label, fs, color, align, valign, family, pad)
        return e

    def rect(self, x, y, w, h, label=None, **kw):
        return self.shape('rectangle', x, y, w, h, label, **kw)

    def ellipse(self, x, y, w, h, label=None, **kw):
        return self.shape('ellipse', x, y, w, h, label, **kw)

    def diamond(self, x, y, w, h, label=None, **kw):
        return self.shape('diamond', x, y, w, h, label, **kw)

    # ---------- lines and arrows ----------
    def poly(self, pts, typ='arrow', stroke=INK, sw=2, dash=False, head='arrow', tail=None, rough=0, start=None, end=None):
        x0, y0 = pts[0]
        rel = [[px - x0, py - y0] for px, py in pts]
        w = max(abs(p[0]) for p in rel)
        h = max(abs(p[1]) for p in rel)
        e = self.base(typ, x0, y0, w, h, stroke=stroke, sw=sw, style='dashed' if dash else 'solid', rough=rough, rnd=None)
        e.update(points=rel, lastCommittedPoint=None, startBinding=None, endBinding=None,
                 startArrowhead=tail if typ == 'arrow' else None, endArrowhead=head if typ == 'arrow' else None, elbowed=False)
        if typ == 'line':
            e.pop('startArrowhead'); e.pop('endArrowhead'); e.update(startArrowhead=None, endArrowhead=None)
        self.add(e)
        for key, el in (('startBinding', start), ('endBinding', end)):
            if el is not None:
                e[key] = {'elementId': el['id'], 'focus': 0, 'gap': 1}
                el['boundElements'] = (el['boundElements'] or []) + [{'id': e['id'], 'type': 'arrow'}]
        return e

    def line(self, pts, **kw):
        return self.poly(pts, typ='line', **kw)

    @staticmethod
    def anchor(el, side):
        x, y, w, h = el['x'], el['y'], el['width'], el['height']
        return {'r': (x + w, y + h / 2), 'l': (x, y + h / 2), 't': (x + w / 2, y), 'b': (x + w / 2, y + h)}[side]

    def connect(self, a, b, sa='r', sb='l', label=None, color=INK, dash=False, sw=2, fs=12, lx=0, ly=0, head='arrow', tail=None):
        (sx, sy), (ex, ey) = self.anchor(a, sa), self.anchor(b, sb)
        if sa in 'rl' and sb in 'rl':
            mx = (sx + ex) / 2
            pts = [(sx, sy), (mx, sy), (mx, ey), (ex, ey)] if abs(sy - ey) > 1 else [(sx, sy), (ex, ey)]
        elif sa in 'tb' and sb in 'tb':
            my = (sy + ey) / 2
            pts = [(sx, sy), (sx, my), (ex, my), (ex, ey)] if abs(sx - ex) > 1 else [(sx, sy), (ex, ey)]
        elif sa in 'rl':
            pts = [(sx, sy), (ex, sy), (ex, ey)]
        else:
            pts = [(sx, sy), (sx, ey), (ex, ey)]
        e = self.poly(pts, stroke=color, sw=sw, dash=dash, start=a, end=b, head=head, tail=tail)
        if label:
            mx, my = (sx + ex) / 2 + lx, (sy + ey) / 2 + ly
            self.text(mx - len(label) * fs * 0.28, my - fs * 1.4, label, fs=fs, color=color, family=2)
        return e

    # ---------- frames ----------
    def frame_begin(self, x, y, w, h, name):
        fid = self.nid()
        self.frame = {'id': fid, 'x': x, 'y': y, 'w': w, 'h': h, 'name': name}
        self.frame_kids = []

    def frame_end(self):
        f = self.frame
        self.frame = None
        e = self.base('frame', f['x'], f['y'], f['w'], f['h'], stroke='#868e96', sw=1, rnd=None)
        e['id'] = f['id']
        e['name'] = f['name']
        self.els.append(e)  # frame goes after its children
        return e

    # ---------- output ----------
    def save(self, path):
        keep = [e for e in self.els if not (e['type'] == 'text' and not e.get('text') and not e.get('containerId'))]
        data = {'type': 'excalidraw', 'version': 2, 'source': 'https://excalidraw.com', 'elements': keep,
                'appState': {'gridSize': None, 'viewBackgroundColor': '#ffffff'}, 'files': {}}
        with open(path, 'w') as f:
            json.dump(data, f, indent=1)
        return path
