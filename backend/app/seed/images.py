"""Studio-style product pictures for the sample catalogue, drawn with Pillow.

Each picture is a soft-lit object on a plain backdrop with a floor shadow, so the sample shop looks
consistent without shipping stock photos. Staff replace them with real photography in the admin
portal (Products → Images) whenever they like.
"""

import io
import math
from collections.abc import Callable

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SIZE = 1000
_S = 2  # draw at twice the size, then downscale, for smooth edges
W = SIZE * _S

RGB = tuple[int, int, int]
Mask = Image.Image


def _hex(value: str) -> RGB:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _mix(a: RGB, b: RGB, t: float) -> RGB:
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


def _lighter(c: RGB, t: float) -> RGB:
    return _mix(c, (255, 255, 255), t)


def _darker(c: RGB, t: float) -> RGB:
    return _mix(c, (0, 0, 0), t)


def _mask() -> tuple[Mask, ImageDraw.ImageDraw]:
    m = Image.new("L", (W, W), 0)
    return m, ImageDraw.Draw(m)


def _p(*values: float) -> list[int]:
    """Coordinates are written on a 1000-unit grid."""
    return [round(v * _S) for v in values]


class Canvas:
    def __init__(self, backdrop: RGB) -> None:
        top = _lighter(backdrop, 0.35)
        bottom = _darker(backdrop, 0.04)
        grad = Image.linear_gradient("L").resize((W, W))
        self.img = Image.composite(
            Image.new("RGB", (W, W), bottom), Image.new("RGB", (W, W), top), grad
        )
        self.backdrop = backdrop

    def shadow(self, cx: float, cy: float, rx: float, ry: float, strength: float = 0.35) -> None:
        m, d = _mask()
        d.ellipse(_p(cx - rx, cy - ry, cx + rx, cy + ry), fill=round(255 * strength))
        m = m.filter(ImageFilter.GaussianBlur(28 * _S))
        self.img = Image.composite(
            Image.new("RGB", (W, W), _darker(self.backdrop, 0.45)), self.img, m
        )

    def fill(self, mask: Mask, color: RGB, shade: float = 0.22, flat: bool = False) -> None:
        """Paint a shape lit softly from the left, falling off to the right."""
        box = mask.getbbox()
        if box is None:
            return
        if flat:
            layer = Image.new("RGB", (W, W), color)
        else:
            x0, _, x1, _ = box
            width = max(1, x1 - x0)
            ramp = Image.new("L", (width, 1))
            ramp.putdata(
                [
                    round(255 * (0.5 + 0.5 * math.cos(math.pi * (i / width) * 1.15 + 0.55)))
                    for i in range(width)
                ]
            )
            ramp = ramp.resize((width, W))
            light = Image.new("RGB", (width, W), _lighter(color, shade * 0.9))
            dark = Image.new("RGB", (width, W), _darker(color, shade))
            strip = Image.composite(light, dark, ramp)
            layer = Image.new("RGB", (W, W), color)
            layer.paste(strip, (x0, 0))
        self.img = Image.composite(layer, self.img, mask)

    def line(self, pts: list[float], color: RGB, width: float) -> None:
        d = ImageDraw.Draw(self.img)
        d.line(_p(*pts), fill=color, width=round(width * _S), joint="curve")

    def render(self) -> bytes:
        out = io.BytesIO()
        self.img.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(
            out, "JPEG", quality=88, optimize=True, progressive=True
        )
        return out.getvalue()


# ---------- Shapes ----------


def _rr(box: tuple[float, float, float, float], r: float) -> Mask:
    m, d = _mask()
    d.rounded_rectangle(_p(*box), radius=round(r * _S), fill=255)
    return m


def _ellipse(box: tuple[float, float, float, float]) -> Mask:
    m, d = _mask()
    d.ellipse(_p(*box), fill=255)
    return m


def _poly(points: list[tuple[float, float]]) -> Mask:
    m, d = _mask()
    d.polygon([(round(x * _S), round(y * _S)) for x, y in points], fill=255)
    return m


def _ring(box: tuple[float, float, float, float], width: float) -> Mask:
    m, d = _mask()
    d.ellipse(_p(*box), outline=255, width=round(width * _S))
    return m


def _arc(box: tuple[float, float, float, float], start: float, end: float, width: float) -> Mask:
    m, d = _mask()
    d.arc(_p(*box), start, end, fill=255, width=round(width * _S))
    return m


def _union(*masks: Mask) -> Mask:
    out = masks[0]
    for m in masks[1:]:
        out = ImageChops.lighter(out, m)
    return out


def _cylinder(
    c: Canvas, x0: float, x1: float, top: float, bottom: float, color: RGB, rim: RGB | None = None
) -> None:
    """An upright cylinder seen slightly from above."""
    ry = (x1 - x0) * 0.09
    body = _union(_rr((x0, top, x1, bottom), 8), _ellipse((x0, bottom - ry, x1, bottom + ry)))
    c.fill(body, color)
    c.fill(_ellipse((x0, top - ry, x1, top + ry)), rim or _lighter(color, 0.25), flat=True)


# ---------- Objects ----------
# Each draws one product, centred, standing on the floor at y ~ 800.


def mug(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(540, 800, 230, 34)
    c.fill(_ring((620, 430, 820, 690), 44), _darker(col, 0.05))
    _cylinder(c, 360, 700, 360, 790, col, rim=_darker(col, 0.25))
    c.fill(_ellipse((378, 345, 682, 381)), _darker(col, 0.45), flat=True)


def tumbler(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 820, 170, 28)
    c.fill(_poly([(375, 300), (625, 300), (590, 810), (410, 810)]), col)
    c.fill(_rr((365, 255, 635, 320), 14), acc)
    c.fill(_rr((470, 180, 500, 262), 8), _darker(acc, 0.2))


def bottle(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 830, 150, 26)
    c.fill(_rr((390, 270, 610, 830), 70), col)
    c.fill(_rr((430, 200, 570, 290), 22), acc)
    c.fill(_ring((450, 150, 550, 230), 18), acc)
    c.fill(_rr((390, 470, 610, 520), 0), _darker(col, 0.12), flat=True)


def carafe(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 820, 210, 30)
    body = _union(_ellipse((300, 440, 700, 830)), _rr((440, 220, 560, 520), 20))
    glass = _lighter(col, 0.55)
    c.fill(body, glass, shade=0.12)
    c.fill(_ellipse((320, 600, 680, 820)), _mix(glass, col, 0.5), shade=0.12)
    c.fill(_rr((430, 200, 570, 240), 12), acc)


def pump_bottle(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 830, 160, 26)
    c.fill(_rr((380, 330, 620, 830), 46), col)
    c.fill(_rr((410, 470, 590, 660), 6), _lighter(col, 0.75), flat=True)
    c.fill(_rr((455, 240, 545, 340), 10), acc)
    c.fill(_rr((475, 190, 525, 250), 6), acc)
    c.fill(_rr((420, 180, 530, 215), 10), acc)


def bowl(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 760, 280, 40)
    m, d = _mask()
    d.chord(_p(220, 300, 780, 800), 0, 180, fill=255)
    c.fill(m, col)
    c.fill(_ellipse((220, 510, 780, 590)), _lighter(col, 0.3), flat=True)
    c.fill(_ellipse((245, 522, 755, 580)), _darker(col, 0.18), flat=True)
    c.fill(_rr((430, 780, 570, 800), 6), _darker(col, 0.2), flat=True)


def plates(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 720, 330, 50)
    for i, y in enumerate((640, 600, 560)):
        c.fill(_ellipse((170, y - 110, 830, y + 70)), _darker(col, 0.12 - i * 0.04), shade=0.08)
        c.fill(_ellipse((170, y - 120, 830, y + 50)), _lighter(col, 0.1), flat=True)
    c.fill(_ellipse((290, 470, 710, 580)), _darker(col, 0.05), flat=True)
    c.fill(_ring((200, 438, 800, 612), 10), acc)


def candle(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 800, 220, 34)
    _cylinder(c, 310, 690, 400, 790, col, rim=_lighter(col, 0.35))
    c.fill(_rr((310, 520, 690, 690), 0), _lighter(col, 0.8), flat=True)
    c.fill(_rr((370, 585, 630, 600), 4), acc, flat=True)
    c.fill(_ellipse((335, 378, 665, 418)), _lighter(acc, 0.7), flat=True)
    c.line([500, 395, 500, 350], _darker(col, 0.6), 7)


def vase(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 830, 180, 30)
    body = _union(_ellipse((300, 380, 700, 830)), _rr((420, 200, 580, 480), 30))
    c.fill(body, col)
    c.fill(_ellipse((410, 185, 590, 225)), _darker(col, 0.35), flat=True)
    c.line([610, 70, 560, 200], _darker(acc, 0.3), 9)
    c.line([450, 40, 480, 200], _darker(acc, 0.3), 9)
    c.fill(_ellipse((570, 30, 670, 110)), acc, shade=0.1)
    c.fill(_ellipse((400, 0, 500, 80)), _lighter(acc, 0.25), shade=0.1)


def diffuser(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 830, 170, 28)
    for x in (360, 430, 500, 570, 640):
        c.line([500, 430, x, 100 + abs(x - 500) * 0.4], _darker(acc, 0.35), 9)
    c.fill(_rr((370, 430, 630, 830), 60), _lighter(col, 0.35), shade=0.15)
    c.fill(_rr((385, 560, 615, 815), 50), col, shade=0.15)
    c.fill(_rr((450, 395, 550, 445), 10), acc)


def cushion(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 800, 300, 40)
    m, d = _mask()
    pts = []
    for i in range(4):
        corner = [(190, 210), (810, 210), (810, 790), (190, 790)][i]
        nxt = [(190, 210), (810, 210), (810, 790), (190, 790)][(i + 1) % 4]
        for t in range(20):
            f = t / 20
            x = corner[0] + (nxt[0] - corner[0]) * f
            y = corner[1] + (nxt[1] - corner[1]) * f
            bow = math.sin(math.pi * f) * 32
            cx, cy = x - 500, y - 500
            n = math.hypot(cx, cy) or 1
            pts.append((x - cx / n * bow, y - cy / n * bow))
    d.polygon([(round(x * _S), round(y * _S)) for x, y in pts], fill=255)
    c.fill(m, col, shade=0.16)
    for k in range(1, 5):
        y = 210 + k * 116
        c.line([230, y, 770, y], _darker(col, 0.08), 6)
    c.line([200, 790, 800, 790], _darker(col, 0.25), 6)
    c.fill(_ellipse((440, 440, 560, 560)), acc)


def throw(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 790, 330, 36)
    for i, (y0, y1) in enumerate(((620, 790), (480, 640), (340, 500))):
        tone = _darker(col, 0.06 * i) if i % 2 == 0 else _mix(col, acc, 0.35)
        c.fill(_rr((180 + i * 8, y0, 820 - i * 8, y1), 40), tone, shade=0.12)
        for x in range(200 + i * 8, 800 - i * 8, 60):
            c.line([x, y0 + 30, x, y1 - 30], _lighter(tone, 0.08), 5)
    for x in range(200, 800, 22):
        c.line([x, 790, x, 820], _darker(col, 0.1), 6)


def tote(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 830, 280, 36)
    c.fill(_arc((350, 130, 650, 520), 180, 360, 34), _darker(acc, 0.1))
    c.fill(_poly([(240, 340), (760, 340), (800, 830), (200, 830)]), col, shade=0.16)
    c.fill(_rr((240, 340, 760, 400), 0), _darker(col, 0.1), flat=True)
    c.fill(_rr((420, 560, 580, 620), 6), acc, flat=True)


def backpack(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 840, 250, 34)
    c.fill(_arc((420, 120, 580, 300), 180, 360, 26), _darker(col, 0.25))
    c.fill(_rr((270, 200, 730, 840), 120), col)
    c.fill(_rr((320, 520, 680, 800), 60), _darker(col, 0.12))
    c.line([340, 560, 660, 560], _darker(col, 0.35), 6)
    c.fill(_rr((475, 545, 525, 600), 8), acc, flat=True)
    c.fill(_rr((420, 320, 580, 345), 10), acc, flat=True)


def wallet(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 720, 300, 36)
    c.fill(_rr((190, 340, 810, 720), 34), col, shade=0.14)
    c.fill(_rr((190, 340, 810, 500), 34), _darker(col, 0.1), shade=0.14)
    c.line([230, 498, 770, 498], _lighter(col, 0.25), 4)
    c.fill(_rr((470, 470, 530, 530), 10), acc, flat=True)


def card_holder(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 760, 220, 30)
    c.fill(_rr((300, 270, 700, 520), 18), _lighter(acc, 0.6), flat=True)
    c.fill(_rr((270, 360, 730, 760), 30), col, shade=0.14)
    c.line([290, 430, 710, 430], _darker(col, 0.25), 5)
    c.line([290, 530, 710, 530], _darker(col, 0.25), 5)


def duffel(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 800, 360, 40)
    c.fill(_arc((330, 240, 670, 560), 180, 360, 30), _darker(acc, 0.1))
    c.fill(_rr((130, 380, 870, 800), 170), col)
    c.fill(_ellipse((130, 400, 300, 790)), _darker(col, 0.12), flat=True)
    c.fill(_ellipse((700, 400, 870, 790)), _darker(col, 0.2), flat=True)
    c.line([280, 420, 720, 420], acc, 8)
    c.fill(_rr((430, 540, 570, 600), 8), acc, flat=True)


def notebook(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 830, 260, 30)
    c.fill(_rr((300, 200, 720, 820), 18), _lighter(col, 0.85), flat=True)
    c.fill(_rr((280, 180, 700, 810), 18), col, shade=0.12)
    c.fill(_rr((610, 180, 640, 810), 0), _darker(acc, 0.1), flat=True)
    c.fill(_rr((340, 640, 520, 700), 4), _lighter(col, 0.3), flat=True)


def pen(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 720, 340, 30, strength=0.25)
    m = _union(_rr((140, 470, 760, 530), 30), _poly([(760, 475), (860, 500), (760, 525)]))
    rot = m.rotate(18, resample=Image.Resampling.BICUBIC, center=(W // 2, W // 2))
    c.fill(rot, col, shade=0.18)
    clip = _rr((280, 460, 300, 540), 4).rotate(18, center=(W // 2, W // 2))
    c.fill(clip, acc, flat=True)
    band = _rr((680, 470, 700, 530), 0).rotate(18, center=(W // 2, W // 2))
    c.fill(band, acc, flat=True)


def desk_tray(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 760, 340, 34)
    c.fill(_poly([(170, 470), (830, 470), (790, 560), (210, 560)]), _darker(col, 0.25), flat=True)
    c.fill(_rr((170, 540, 830, 760), 24), col)
    c.line([400, 560, 400, 740], _darker(col, 0.15), 6)
    c.line([600, 560, 600, 740], _darker(col, 0.15), 6)
    c.line([300, 330, 260, 510], _darker(acc, 0.1), 16)
    c.line([340, 300, 330, 510], acc, 16)


def headphones(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 820, 280, 34)
    c.fill(_arc((230, 150, 770, 700), 180, 360, 50), col)
    c.fill(_arc((250, 170, 750, 680), 195, 345, 18), _darker(acc, 0.1))
    for x in (200, 650):
        c.fill(_rr((x, 420, x + 150, 760), 70), _darker(col, 0.08))
        c.fill(
            _rr((x + (110 if x < 500 else 0), 450, x + (150 if x < 500 else 40), 730), 20),
            _darker(col, 0.35),
            flat=True,
        )


def speaker(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 830, 300, 34)
    c.fill(_rr((220, 300, 780, 830), 90), col)
    d = ImageDraw.Draw(c.img)
    dot = _darker(col, 0.28)
    for gy in range(360, 660, 26):
        for gx in range(280, 730, 26):
            if (gx - 500) ** 2 / 210**2 + (gy - 505) ** 2 / 150**2 <= 1:
                d.ellipse(_p(gx - 6, gy - 6, gx + 6, gy + 6), fill=dot)
    c.fill(_rr((440, 720, 560, 745), 10), acc, flat=True)


def earbuds(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 780, 230, 32)
    c.fill(_rr((300, 380, 700, 780), 140), col, shade=0.15)
    c.line([310, 520, 690, 520], _darker(col, 0.15), 5)
    c.fill(_ellipse((488, 600, 512, 624)), acc, flat=True)


def charger(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 720, 300, 46)
    c.fill(_ellipse((200, 470, 800, 730)), _darker(col, 0.2), flat=True)
    c.fill(_ellipse((200, 440, 800, 700)), col, shade=0.12)
    c.fill(_ring((380, 530, 620, 610), 8), acc)
    c.line([780, 590, 900, 640, 990, 640], _darker(col, 0.25), 14)


def watch(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 830, 170, 26)
    c.fill(_rr((420, 100, 580, 900), 40), col, shade=0.16)
    c.fill(_ellipse((310, 310, 690, 690)), _darker(acc, 0.05))
    c.fill(_ellipse((340, 340, 660, 660)), _lighter(acc, 0.85), flat=True)
    for k in range(12):
        a = k * math.pi / 6
        c.line(
            [
                500 + 140 * math.sin(a),
                500 - 140 * math.cos(a),
                500 + 155 * math.sin(a),
                500 - 155 * math.cos(a),
            ],
            _darker(acc, 0.3),
            5,
        )
    c.line([500, 500, 500, 390], _darker(acc, 0.5), 9)
    c.line([500, 500, 580, 540], _darker(acc, 0.5), 7)
    c.fill(_rr((688, 480, 712, 520), 6), _darker(acc, 0.05), flat=True)


def soap(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 760, 300, 36)
    c.fill(_rr((230, 560, 770, 760), 70), _darker(col, 0.08))
    c.fill(_rr((280, 400, 720, 590), 70), col)
    c.fill(_rr((420, 470, 580, 520), 20), _darker(col, 0.12), flat=True)
    c.fill(_rr((300, 590, 700, 600), 0), _darker(col, 0.2), flat=True)


def glasses(c: Canvas, col: RGB, acc: RGB) -> None:
    c.shadow(500, 800, 300, 30)
    for x0 in (230, 520):
        glass = _lighter(col, 0.6)
        c.fill(
            _poly([(x0, 420), (x0 + 250, 420), (x0 + 225, 800), (x0 + 25, 800)]), glass, shade=0.1
        )
        c.fill(
            _poly([(x0 + 15, 620), (x0 + 237, 620), (x0 + 225, 800), (x0 + 25, 800)]),
            _mix(glass, acc, 0.4),
            shade=0.1,
        )
        c.fill(_ellipse((x0, 405, x0 + 250, 440)), _lighter(col, 0.8), flat=True)


DRAWERS: dict[str, Callable[[Canvas, RGB, RGB], None]] = {
    f.__name__: f
    for f in (
        mug,
        tumbler,
        bottle,
        carafe,
        pump_bottle,
        bowl,
        plates,
        candle,
        vase,
        diffuser,
        cushion,
        throw,
        tote,
        backpack,
        wallet,
        card_holder,
        duffel,
        notebook,
        pen,
        desk_tray,
        headphones,
        speaker,
        earbuds,
        charger,
        watch,
        soap,
        glasses,
    )
}


def draw(kind: str, color: str, accent: str, backdrop: str) -> bytes:
    """A 1000 x 1000 JPEG of one product."""
    canvas = Canvas(_hex(backdrop))
    DRAWERS[kind](canvas, _hex(color), _hex(accent))
    return canvas.render()
