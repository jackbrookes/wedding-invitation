from __future__ import annotations

import struct
import sys
from pathlib import Path

from PIL import Image


WHITE = (255, 250, 243)


def pack_pascal(text: str) -> bytes:
    raw = text.encode("ascii", "replace")[:255]
    value = bytes([len(raw)]) + raw
    return value + b"\x00" * ((4 - (len(value) % 4)) % 4)


def extract_foreground(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    pixels = list(rgb.getdata())
    bg = pixels[0]
    channels = [max(1, WHITE[i] - bg[i]) for i in range(3)]
    out = Image.new("RGBA", rgb.size, WHITE + (0,))
    alpha = []
    for pixel in pixels:
        estimate = sum(max(0.0, min(1.0, (pixel[i] - bg[i]) / channels[i])) for i in range(3)) / 3
        alpha.append(round(estimate * 255))
    out.putalpha(Image.frombytes("L", rgb.size, bytes(alpha)))
    return out


def split_layers(image: Image.Image) -> list[tuple[str, Image.Image]]:
    width, height = image.size
    foreground = extract_foreground(image)
    alpha = foreground.getchannel("A")
    alpha_data = alpha.load()

    background = Image.new("RGBA", (width, height), image.getpixel((0, 0))[:3] + (255,))
    border = Image.new("RGBA", (width, height), WHITE + (0,))
    header = Image.new("RGBA", (width, height), WHITE + (0,))
    schedule = Image.new("RGBA", (width, height), WHITE + (0,))
    border_alpha = border.getchannel("A")
    header_alpha = header.getchannel("A")
    schedule_alpha = schedule.getchannel("A")
    border_px = border_alpha.load()
    header_px = header_alpha.load()
    schedule_px = schedule_alpha.load()
    src_rgb = foreground.convert("RGB")

    cx = width / 2
    rx = width / 2 - 72
    cy = 600
    ry = 540
    for y in range(height):
        for x in range(width):
            a = alpha_data[x, y]
            if not a:
                continue
            arc_distance = abs(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 - 1)
            is_border = x < 95 or x >= width - 95 or (y < 700 and arc_distance < 0.032)
            target = border_px if is_border else header_px if y < 1370 else schedule_px
            target[x, y] = a

    border.putalpha(border_alpha)
    header.putalpha(header_alpha)
    schedule.putalpha(schedule_alpha)
    for layer in (border, header, schedule):
        layer_rgb = layer.convert("RGB")
        layer_rgb.putalpha(layer.getchannel("A"))

    return [
        ("Background", background),
        ("Arched Border", border),
        ("Header, Names & Date", header),
        ("Programme Schedule", schedule),
    ]


def channel_payload(image: Image.Image) -> bytes:
    rgba = image.convert("RGBA")
    channels = [rgba.getchannel(name).tobytes() for name in ("R", "G", "B", "A")]
    return b"".join(struct.pack(">H", 0) + channel for channel in channels)


def layer_record(name: str, image: Image.Image) -> tuple[bytes, bytes]:
    width, height = image.size
    payload = channel_payload(image)
    channels = []
    channel_size = width * height + 2
    for channel_id in (0, 1, 2, -1):
        channels.append(struct.pack(">hI", channel_id, channel_size))
    record = struct.pack(">iiiiH", 0, 0, height, width, 4)
    record += b"".join(channels)
    record += b"8BIMnorm" + bytes([255, 0, 0, 0])
    extra = struct.pack(">I", 0) + struct.pack(">I", 0) + pack_pascal(name)
    record += struct.pack(">I", len(extra)) + extra
    return record, payload


def resolution_resource(dpi: int = 300) -> bytes:
    fixed = int(dpi * 65536)
    data = struct.pack(">IHHIHH", fixed, 1, 1, fixed, 1, 1)
    return b"8BIM" + struct.pack(">H", 0x03) + b"\x00\x00" + struct.pack(">I", len(data)) + data


def write_psd(source: Path, destination: Path) -> None:
    image = Image.open(source).convert("RGB")
    width, height = image.size
    layers = split_layers(image)
    records, payloads = zip(*(layer_record(name, layer) for name, layer in layers))
    layer_info = struct.pack(">h", len(layers)) + b"".join(records) + b"".join(payloads)
    layer_mask = struct.pack(">I", len(layer_info)) + layer_info + struct.pack(">I", 0)
    resources = resolution_resource()
    header = b"8BPS" + struct.pack(">H", 1) + b"\x00" * 6 + struct.pack(">HIIHH", 4, height, width, 8, 3)
    composite = struct.pack(">H", 0) + b"".join(image.getchannel(channel).tobytes() for channel in ("R", "G", "B")) + bytes(width * height)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as stream:
        stream.write(header)
        stream.write(struct.pack(">I", 0))
        stream.write(struct.pack(">I", len(resources)))
        stream.write(resources)
        stream.write(struct.pack(">I", len(layer_mask)))
        stream.write(layer_mask)
        stream.write(composite)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_layered_psd.py INPUT_PNG OUTPUT_PSD")
    write_psd(Path(sys.argv[1]), Path(sys.argv[2]))
