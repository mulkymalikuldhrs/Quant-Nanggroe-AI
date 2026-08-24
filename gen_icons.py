"""Generate QNA icon set — SVG master + PNG exports for all platforms.

Creates a single SVG icon (golden "Q" with candlestick accent on dark bg)
and exports PNG at all required sizes for:
  - favicon.ico / favicon-16/32.png
  - dashboard/public/logo192.png, logo512.png
  - tray icon
  - desktop shortcut icon (.ico multi-size)
"""
import pathlib
import subprocess

ROOT = pathlib.Path(r"D:\repositories\Quant-Nanggroe-AI-worktree")
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0a0a14"/>
      <stop offset="100%" stop-color="#050510"/>
    </linearGradient>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#FFD700"/>
      <stop offset="100%" stop-color="#FFA500"/>
    </linearGradient>
    <linearGradient id="teal" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#00E5AA"/>
      <stop offset="100%" stop-color="#00B894"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <!-- Background rounded square -->
  <rect width="512" height="512" rx="96" fill="url(#bg)"/>

  <!-- Subtle grid pattern -->
  <g opacity="0.04" stroke="#ffffff" stroke-width="1">
    <line x1="128" y1="0" x2="128" y2="512"/>
    <line x1="256" y1="0" x2="256" y2="512"/>
    <line x1="384" y1="0" x2="384" y2="512"/>
    <line x1="0" y1="128" x2="512" y2="128"/>
    <line x1="0" y1="256" x2="512" y2="256"/>
    <line x1="0" y1="384" x2="512" y2="384"/>
  </g>

  <!-- Q letter — bold geometric -->
  <text x="216" y="340"
        font-family="Georgia, 'Times New Roman', serif"
        font-size="280"
        font-weight="bold"
        fill="url(#gold)"
        text-anchor="middle">Q</text>

  <!-- Candlestick accents (right of Q) -->
  <g filter="url(#glow)">
    <!-- Bull candle -->
    <rect x="330" y="160" width="16" height="80" rx="3" fill="url(#teal)"/>
    <line x1="338" y1="140" x2="338" y2="170" stroke="url(#teal)" stroke-width="3"/>
    <line x1="338" y1="240" x2="338" y2="260" stroke="url(#teal)" stroke-width="3"/>
    <!-- Bear candle -->
    <rect x="360" y="200" width="16" height="70" rx="3" fill="#ef4444"/>
    <line x1="368" y1="185" x2="368" y2="210" stroke="#ef4444" stroke-width="3"/>
    <line x1="368" y1="270" x2="368" y2="290" stroke="#ef4444" stroke-width="3"/>
    <!-- Bull candle (smaller) -->
    <rect x="390" y="230" width="14" height="60" rx="3" fill="url(#teal)"/>
    <line x1="397" y1="215" x2="397" y2="240" stroke="url(#teal)" stroke-width="2.5"/>
    <line x1="397" y1="290" x2="397" y2="308" stroke="url(#teal)" stroke-width="2.5"/>
  </g>

  <!-- Bottom accent line -->
  <rect x="96" y="400" width="320" height="4" rx="2" fill="url(#gold)" opacity="0.6"/>

  <!-- Nanggroe pattern hint (top-right corner, subtle) -->
  <g opacity="0.08" fill="#FFD700">
    <path d="M420 48 L440 28 L460 48 L440 68 Z"/>
    <path d="M450 78 L470 58 L490 78 L470 98 Z"/>
  </g>
</svg>"""

# Write SVG master
svg_path = ASSETS / "qna-icon.svg"
svg_path.write_text(SVG, encoding="utf-8")
print(f"SVG written: {svg_path}")

# Export PNG sizes using Python (no external tools needed)
try:
    import struct
    from io import BytesIO

    # Try cairosvg first (best quality)
    try:
        import cairosvg
        for size in [16, 32, 48, 64, 128, 192, 256, 512]:
            out = ASSETS / f"icon-{size}.png"
            cairosvg.svg2png(url=str(svg_path), write_to=str(out),
                             output_width=size, output_height=size)
            print(f"PNG: {out.name} ({size}x{size})")

        # ICO (multi-size)
        ico_path = ROOT / "dashboard" / "public" / "favicon.ico"
        ico_path.parent.mkdir(parents=True, exist_ok=True)
        # Use largest PNG as base for ICO via PIL if available
        try:
            from PIL import Image
            img = Image.open(str(ASSETS / "icon-256.png"))
            img.save(str(ico_path), format="ICO",
                     sizes=[(16, 16), (32, 32), (48, 48)])
            print(f"ICO: {ico_path}")
        except ImportError:
            print("PIL not available — skip .ico generation")

    except ImportError:
        print("cairosvg not installed — generating simple PNG via PIL")
        from PIL import Image, ImageDraw, ImageFont

        def draw_icon(size: int) -> Image.Image:
            img = Image.new("RGBA", (size, size), (10, 10, 20, 255))
            draw = ImageDraw.Draw(img)

            # Rounded rectangle background
            r = size // 5
            draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r,
                                   fill=(10, 10, 20, 255))

            # Gold "Q" text
            font_size = int(size * 0.55)
            try:
                from PIL import ImageFont
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            # Draw Q centered-left
            bbox = draw.textbbox((0, 0), "Q", font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            qx = int(size * 0.15)
            qy = int((size - th) // 2)
            draw.text((qx, qy), "Q", fill=(255, 215, 0, 255), font=font)

            # Teal candlestick bars on right
            bar_w = max(int(size * 0.03), 2)
            gap_x = int(size * 0.62)
            # Bull candle
            draw.rectangle([gap_x, int(size*0.3), gap_x + bar_w, int(size*0.5)],
                           fill=(0, 229, 170, 255))
            # Bear candle
            draw.rectangle([gap_x + bar_w * 2, int(size*0.4),
                            gap_x + bar_w * 3, int(size*0.58)],
                           fill=(239, 68, 68, 255))

            return img

        for size in [16, 32, 48, 64, 128, 192, 256, 512]:
            img = draw_icon(size)
            out = ASSETS / f"icon-{size}.png"
            img.save(str(out), "PNG")
            print(f"PNG: {out.name}")

        # Copy to dashboard public
        pub = ROOT / "dashboard" / "public"
        pub.mkdir(parents=True, exist_ok=True)
        for name in ["icon-192.png", "icon-512.png"]:
            src = ASSETS / name
            dst = pub / name
            shutil.copy2(src, dst)
            print(f"Copied: {dst}")

except Exception as e:
    print(f"Icon generation error: {e}")
