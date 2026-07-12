"""Simple SVG captcha generator. No external dependencies."""

from __future__ import annotations

import random
import string


def generate_code(length: int = 4) -> str:
    """Generate a random alphanumeric code (excluding ambiguous chars)."""
    chars = string.ascii_uppercase.replace("O", "").replace("I", "") + string.digits.replace("0", "").replace("1", "")
    return "".join(random.choices(chars, k=length))


def _random_color(min_val: int = 0, max_val: int = 150) -> str:
    return f"rgb({random.randint(min_val, max_val)},{random.randint(min_val, max_val)},{random.randint(min_val, max_val)})"


def render_svg(code: str) -> str:
    """Render captcha code as an SVG image with noise."""
    width = 120
    height = 44
    char_spacing = 26
    start_x = 10

    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']

    # Background
    lines.append(f'<rect width="{width}" height="{height}" fill="#f8f9fa" rx="4" />')

    # Noise lines
    for _ in range(random.randint(4, 7)):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{_random_color(100, 200)}" stroke-width="{random.uniform(0.5, 1.5)}" opacity="0.6" />')

    # Noise dots
    for _ in range(random.randint(30, 50)):
        x = random.randint(0, width)
        y = random.randint(0, height)
        lines.append(f'<circle cx="{x}" cy="{y}" r="{random.uniform(0.5, 1.5)}" fill="{_random_color()}" opacity="0.4" />')

    # Characters with individual styling
    for i, ch in enumerate(code):
        x = start_x + i * char_spacing
        y = random.randint(30, 36)
        angle = random.randint(-20, 20)
        color = _random_color(30, 170)
        lines.append(
            f'<text x="{x}" y="{y}" fill="{color}" '
            f'font-size="22" font-family="monospace" font-weight="bold" '
            f'transform="rotate({angle},{x},{y})">{ch}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)
