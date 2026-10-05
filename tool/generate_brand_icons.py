#!/usr/bin/env python3
"""Render every TENVPN app icon from assets_source/images/brand/logo.png.

Usage: python tool/generate_brand_icons.py   (needs Pillow)

The logo is a light mark on a near-black square, so the launcher background
is black and the Android monochrome layer is the logo's luminance mask.
"""
import base64
import io
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'assets_source/images/brand/logo.png'
BACKGROUND = (0, 0, 0)
DENSITIES = {'mdpi': 1, 'hdpi': 1.5, 'xhdpi': 2, 'xxhdpi': 3, 'xxxhdpi': 4}
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
TRAY_ICO_SIZES = [16, 20, 24, 32, 40, 48, 64]


def load_mark() -> Image.Image:
    src = Image.open(SOURCE).convert('RGB')
    lum = ImageOps.grayscale(src)
    bbox = lum.point(lambda v: 255 if v > 40 else 0).getbbox()
    mark = src.crop(bbox)
    alpha = lum.crop(bbox).point(lambda v: 0 if v < 18 else min(255, (v - 18) * 6))
    mark.putalpha(alpha)
    return mark


def fit(mark: Image.Image, size: int, fraction: float, bg=BACKGROUND) -> Image.Image:
    canvas = Image.new('RGBA', (size, size), bg + (255,) if bg else (0, 0, 0, 0))
    scale = size * fraction / max(mark.size)
    w, h = round(mark.width * scale), round(mark.height * scale)
    m = mark.resize((w, h), Image.LANCZOS)
    canvas.alpha_composite(m, ((size - w) // 2, (size - h) // 2))
    return canvas


def round_mask(img: Image.Image) -> Image.Image:
    mask = Image.new('L', (img.width * 4, img.height * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, mask.width - 1, mask.height - 1), fill=255)
    mask = mask.resize(img.size, Image.LANCZOS)
    out = img.copy()
    out.putalpha(ImageChops.multiply(out.getchannel('A'), mask))
    return out


def monochrome(mark: Image.Image, size: int, fraction: float) -> Image.Image:
    lum = ImageOps.grayscale(mark.convert('RGB'))
    alpha = ImageChops.multiply(lum.point(lambda v: 0 if v < 60 else 255), mark.getchannel('A'))
    white = Image.new('RGBA', mark.size, (255, 255, 255, 0))
    white.putalpha(alpha)
    return fit(white, size, fraction, bg=None)


def save_ico(img: Image.Image, path: Path, sizes):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format='ICO', sizes=[(s, s) for s in sizes])


def svg_with_png(img: Image.Image, path: Path):
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    data = base64.b64encode(buf.getvalue()).decode()
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{img.width}" height="{img.height}" viewBox="0 0 {img.width} {img.height}">'
        f'<image width="{img.width}" height="{img.height}" '
        f'xlink:href="data:image/png;base64,{data}"/></svg>\n',
        encoding='utf-8',
    )


def dim(img: Image.Image) -> Image.Image:
    grey = ImageOps.grayscale(img.convert('RGB')).convert('RGBA')
    grey.putalpha(img.getchannel('A'))
    return grey


def main():
    mark = load_mark()
    res = ROOT / 'android/app/src/main/res'
    for name, k in DENSITIES.items():
        d = res / f'mipmap-{name}'
        d.mkdir(exist_ok=True)
        legacy = fit(mark, round(48 * k), 0.84)
        legacy.save(d / 'ic_launcher.webp', lossless=True)
        round_mask(fit(mark, round(48 * k), 0.74)).save(d / 'ic_launcher_round.webp', lossless=True)
        fit(mark, round(108 * k), 0.60, bg=None).save(d / 'ic_launcher_foreground.png')
        monochrome(mark, round(108 * k), 0.60).save(d / 'ic_launcher_monochrome.png')
        tv = res / f'mipmap-television-{name}'
        if tv.exists():
            fit(mark, round(80 * k), 0.84).save(tv / 'ic_launcher.webp', lossless=True)
    banner = Image.new('RGBA', (320, 180), BACKGROUND + (255,))
    b = fit(mark, 160, 0.95, bg=None)
    banner.alpha_composite(b, (80, 10))
    banner.save(res / 'mipmap-xhdpi/ic_banner.png')

    master = fit(mark, 1024, 0.86)
    save_ico(master, ROOT / 'windows/runner/resources/app_icon.ico', ICO_SIZES)
    tray = fit(mark, 256, 1.0, bg=None)
    save_ico(dim(tray), ROOT / 'assets/images/tray/windows/status_1.ico', TRAY_ICO_SIZES)
    save_ico(tray, ROOT / 'assets/images/tray/windows/status_2.ico', TRAY_ICO_SIZES)
    save_ico(tray, ROOT / 'assets/images/tray/windows/status_3.ico', TRAY_ICO_SIZES)
    unix = ROOT / 'assets/images/tray/unix'
    for scale, sub in ((1, ''), (2, '2.0x'), (3, '3.0x'), (4, '4.0x')):
        d = unix / sub if sub else unix
        if d.exists():
            s = 18 * scale
            dim(fit(mark, s, 1.0, bg=None)).save(d / 'status_1.png')
            fit(mark, s, 1.0, bg=None).save(d / 'status_2.png')
            fit(mark, s, 1.0, bg=None).save(d / 'status_3.png')

    svg_with_png(fit(mark, 256, 0.92), ROOT / 'assets/images/icon.svg')
    master.convert('RGB').save(ROOT / 'assets/images/icon.png')
    save_ico(master, ROOT / 'assets/images/icon.ico', ICO_SIZES)

    composer = ROOT / 'ios/Runner/AppIcon.icon'
    svg_with_png(fit(mark, 1024, 0.86), composer / 'Assets/icon.svg')
    spec = json.loads((composer / 'icon.json').read_text(encoding='utf-8'))
    spec['fill'] = {'solid': 'srgb:0.00000,0.00000,0.00000,1.00000'}
    for group in spec.get('groups', []):
        for layer in group.get('layers', []):
            layer['position'] = {'scale': 1.0, 'translation-in-points': [0, 0]}
    (composer / 'icon.json').write_text(json.dumps(spec, indent=2) + '\n', encoding='utf-8')

    widget = ROOT / 'ios/Widget/Assets.xcassets/AppIcon.appiconset'
    master.convert('RGB').save(widget / 'AppIcon-1024.png')
    contents = json.loads((widget / 'Contents.json').read_text(encoding='utf-8'))
    contents['images'][0]['filename'] = 'AppIcon-1024.png'
    (widget / 'Contents.json').write_text(json.dumps(contents, indent=2) + '\n', encoding='utf-8')

    launch = ROOT / 'ios/Runner/Assets.xcassets/LaunchLogo.imageset'
    for suffix, k in (('', 1), ('@2x', 2), ('@3x', 3)):
        logo = fit(mark, 288 * k, 0.9, bg=None)
        logo.save(launch / f'LaunchLogo{suffix}.png')
        logo.save(launch / f'LaunchLogoDark{suffix}.png')
    print('icons written')


if __name__ == '__main__':
    main()
