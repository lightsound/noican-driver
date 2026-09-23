#!/usr/bin/env python3
"""Generates resources/Microphone.icns, the driver's device icon.

A plain white microphone glyph on a flat slate rounded square, drawn from
signed-distance shapes with analytic anti-aliasing and written as a
PNG-based .icns. Standard library only. The pixels are deterministic;
the compressed bytes depend on the zlib build, so `--check` compares
decoded pixels (within one step per channel, for libm rounding) instead
of file bytes.

    python3 scripts/make-icon.py [output.icns] [--png preview.png]
    python3 scripts/make-icon.py --check resources/Microphone.icns
"""

import math
import struct
import sys
import zlib
from pathlib import Path

BACKGROUND = (0x3A, 0x47, 0x55)
GLYPH = (0xFF, 0xFF, 0xFF)

# Geometry on a 1024-unit canvas (y grows downwards). The rounded square
# follows the macOS icon grid: an 824-unit body with a 185-unit radius.
BODY_MIN, BODY_MAX, BODY_RADIUS = 100.0, 924.0, 185.0
CX = 512.0
CAPSULE_TOP, CAPSULE_BOTTOM, CAPSULE_RADIUS = 330.0, 470.0, 80.0
YOKE_CY, YOKE_RADIUS, YOKE_HALF_WIDTH, YOKE_RISE = 480.0, 150.0, 18.0, 50.0
STEM_TOP, STEM_BOTTOM = 630.0, 730.0
BASE_Y, BASE_HALF_LENGTH = 740.0, 100.0
LINE_HALF_WIDTH = 18.0

# (type code, pixel size) for the members iconutil writes for a full
# iconset: 16-512 px plus their @2x variants.
ICNS_MEMBERS = [
    (b"icp4", 16),
    (b"icp5", 32),
    (b"ic07", 128),
    (b"ic08", 256),
    (b"ic09", 512),
    (b"ic10", 1024),
    (b"ic11", 32),
    (b"ic12", 64),
    (b"ic13", 256),
    (b"ic14", 512),
]


def rounded_box(x, y, lo, hi, radius):
    """Signed distance to an axis-aligned square [lo, hi]^2 with round corners."""
    centre = (lo + hi) / 2
    half = (hi - lo) / 2 - radius
    qx = abs(x - centre) - half
    qy = abs(y - centre) - half
    outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
    return outside + min(max(qx, qy), 0.0) - radius


def segment(x, y, ax, ay, bx, by, radius):
    """Signed distance to a capsule around the segment a-b."""
    px, py = x - ax, y - ay
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, (px * dx + py * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - t * dx, py - t * dy) - radius


def glyph(x, y):
    """Signed distance to the microphone: capsule, yoke, stem, and base."""
    d = segment(x, y, CX, CAPSULE_TOP, CX, CAPSULE_BOTTOM, CAPSULE_RADIUS)
    if y >= YOKE_CY:
        ring = abs(math.hypot(x - CX, y - YOKE_CY) - YOKE_RADIUS) - YOKE_HALF_WIDTH
        d = min(d, ring)
    for side in (-1.0, 1.0):
        arm_x = CX + side * YOKE_RADIUS
        d = min(d, segment(x, y, arm_x, YOKE_CY - YOKE_RISE, arm_x, YOKE_CY, YOKE_HALF_WIDTH))
    d = min(d, segment(x, y, CX, STEM_TOP, CX, STEM_BOTTOM, LINE_HALF_WIDTH))
    return min(
        d,
        segment(x, y, CX - BASE_HALF_LENGTH, BASE_Y, CX + BASE_HALF_LENGTH, BASE_Y, LINE_HALF_WIDTH),
    )


def coverage(distance_px):
    return max(0.0, min(1.0, 0.5 - distance_px))


def render(size):
    """Returns RGBA rows for a size x size rendering."""
    scale = 1024.0 / size
    rows = []
    for j in range(size):
        row = bytearray()
        y = (j + 0.5) * scale
        for i in range(size):
            x = (i + 0.5) * scale
            body = coverage(rounded_box(x, y, BODY_MIN, BODY_MAX, BODY_RADIUS) / scale)
            if body == 0.0:
                row += b"\x00\x00\x00\x00"
                continue
            mark = coverage(glyph(x, y) / scale)
            rgb = (round(b + (g - b) * mark) for b, g in zip(BACKGROUND, GLYPH))
            row += bytes((*rgb, round(255 * body)))
        rows.append(bytes(row))
    return rows


def png(size, rows):
    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    raw = b"".join(b"\x00" + row for row in rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def members_of(icns):
    """Yields (type code, PNG bytes) for each member of an icns file."""
    if icns[:4] != b"icns":
        raise ValueError("not an icns file")
    at = 8
    while at < len(icns):
        code, length = icns[at : at + 4], struct.unpack(">I", icns[at + 4 : at + 8])[0]
        yield code, icns[at + 8 : at + length]
        at += length


def png_pixels(data):
    """Decodes the filter-0 RGBA rows this script writes."""
    at, idat, size = 8, b"", 0
    while at < len(data):
        length = struct.unpack(">I", data[at : at + 4])[0]
        tag, body = data[at + 4 : at + 8], data[at + 8 : at + 8 + length]
        if tag == b"IHDR":
            size = struct.unpack(">I", body[:4])[0]
        elif tag == b"IDAT":
            idat += body
        at += length + 12
    raw = zlib.decompress(idat)
    stride = size * 4 + 1
    if any(raw[r * stride] != 0 for r in range(size)):
        raise ValueError("unexpected PNG row filter")
    return size, [raw[r * stride + 1 : (r + 1) * stride] for r in range(size)]


def check(path):
    found = dict(members_of(Path(path).read_bytes()))
    expected = [code for code, _ in ICNS_MEMBERS]
    if sorted(found) != sorted(expected):
        sys.exit(f"{path}: members {sorted(found)} differ from {sorted(expected)}")
    for code, size in ICNS_MEMBERS:
        got_size, got = png_pixels(found[code])
        want = render(size)
        if got_size != size or any(
            abs(a - b) > 1 for g, w in zip(got, want) for a, b in zip(g, w)
        ):
            sys.exit(f"{path}: {code.decode()} does not match scripts/make-icon.py")
    print(f"{path}: matches scripts/make-icon.py")


def main(argv):
    root = Path(__file__).resolve().parent.parent
    args = list(argv)
    if args[:1] == ["--check"]:
        check(args[1])
        return
    preview = None
    if "--png" in args:
        at = args.index("--png")
        preview = Path(args[at + 1])
        del args[at : at + 2]
    output = Path(args[0]) if args else root / "resources" / "Microphone.icns"

    pngs = {size: png(size, render(size)) for size in sorted({s for _, s in ICNS_MEMBERS})}
    members = b"".join(
        code + struct.pack(">I", len(pngs[size]) + 8) + pngs[size] for code, size in ICNS_MEMBERS
    )
    output.write_bytes(b"icns" + struct.pack(">I", len(members) + 8) + members)
    if preview is not None:
        preview.write_bytes(pngs[1024])
    print(output)


if __name__ == "__main__":
    main(sys.argv[1:])
