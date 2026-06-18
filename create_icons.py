#!/usr/bin/env python3
"""
Create PWA icons and cover image for Agentic AI System
Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import os
from pathlib import Path

# Create directories
Path("web_interface/static/icons").mkdir(parents=True, exist_ok=True)
Path("web_interface/static/screenshots").mkdir(parents=True, exist_ok=True)

# Try to create actual images with PIL
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
    print("✅ PIL available - creating actual images")
except ImportError:
    PIL_AVAILABLE = False
    print("❌ PIL not available - creating placeholder files")

def create_icon(size, filename):
    """Create an icon with the specified size"""
    if PIL_AVAILABLE:
        # Create image with gradient background
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Create gradient background (blue to purple)
        for y in range(size):
            r = int(37 + (118 - 37) * y / size)  # 37 to 118
            g = int(99 + (181 - 99) * y / size)  # 99 to 181  
            b = int(235 + (162 - 235) * y / size)  # 235 to 162
            draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
        
        # Add brain icon (simplified circle with inner pattern)
        margin = size // 8
        brain_size = size - 2 * margin
        
        # Outer circle
        draw.ellipse([margin, margin, size - margin, size - margin], 
                    fill=(255, 255, 255, 255), outline=(255, 255, 255, 255), width=2)
        
        # Inner brain pattern (simplified)
        center = size // 2
        inner_margin = size // 4
        
        # Left hemisphere
        draw.arc([inner_margin, inner_margin, center + 5, size - inner_margin], 
                start=0, end=180, fill=(37, 99, 235, 255), width=3)
        
        # Right hemisphere  
        draw.arc([center - 5, inner_margin, size - inner_margin, size - inner_margin], 
                start=0, end=180, fill=(37, 99, 235, 255), width=3)
        
        # Central line
        draw.line([(center, inner_margin + 10), (center, size - inner_margin - 10)], 
                 fill=(37, 99, 235, 255), width=2)
        
        img.save(f"web_interface/static/icons/{filename}")
        print(f"✅ Created icon: {filename} ({size}x{size})")
    else:
        # Create placeholder SVG
        svg_content = f'''<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="grad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style="stop-color:#2563eb;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
        </linearGradient>
    </defs>
    <rect width="{size}" height="{size}" fill="url(#grad)" rx="12"/>
    <circle cx="{size//2}" cy="{size//2}" r="{size//3}" fill="white" opacity="0.9"/>
    <text x="{size//2}" y="{size//2 + 8}" text-anchor="middle" fill="#2563eb" font-family="Arial" font-size="{size//4}" font-weight="bold">🧠</text>
</svg>'''
        
        # Save as SVG (will work as icon)
        with open(f"web_interface/static/icons/{filename.replace('.png', '.svg')}", 'w') as f:
            f.write(svg_content)
        
        # Create PNG placeholder
        with open(f"web_interface/static/icons/{filename}", 'w') as f:
            f.write(f"# Agentic AI Icon {size}x{size}\n# Replace with actual PNG")
        
        print(f"✅ Created placeholder: {filename} ({size}x{size})")

def create_cover_image():
    """Create a cover image for the project"""
    if PIL_AVAILABLE:
        # Create large cover image
        width, height = 1200, 630
        img = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Gradient background
        for y in range(height):
            r = int(102 + (118 - 102) * y / height)
            g = int(126 + (181 - 126) * y / height) 
            b = int(234 + (162 - 234) * y / height)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Try to load a font, fallback to default
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            credit_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()  
            credit_font = ImageFont.load_default()
        
        # Title
        title = "🧠 Agentic AI System"
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) // 2, 150), title, fill=(255, 255, 255), font=title_font)
        
        # Subtitle
        subtitle = "Autonomous Multi-Agent Intelligence with Voice Interaction"
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        draw.text(((width - subtitle_width) // 2, 250), subtitle, fill=(255, 255, 255, 200), font=subtitle_font)
        
        # Features
        features = [
            "✨ 20+ Specialized AI Agents",
            "🎤 Advanced Voice Interaction", 
            "📱 Progressive Web App (PWA)",
            "🚀 Auto-Deploy to Multiple Platforms",
            "🔄 Real-time Agent Creation"
        ]
        
        y_pos = 320
        for feature in features:
            feature_bbox = draw.textbbox((0, 0), feature, font=subtitle_font)
            feature_width = feature_bbox[2] - feature_bbox[0]
            draw.text(((width - feature_width) // 2, y_pos), feature, fill=(255, 255, 255, 180), font=subtitle_font)
            y_pos += 50
        
        # Credit
        credit = "🇮🇩 Made with ❤️ by Mulky Malikul Dhaher in Indonesia"
        credit_bbox = draw.textbbox((0, 0), credit, font=credit_font)
        credit_width = credit_bbox[2] - credit_bbox[0]
        draw.text(((width - credit_width) // 2, height - 80), credit, fill=(255, 255, 255, 150), font=credit_font)
        
        img.save("agentic-ai-cover.png")
        img.save("web_interface/static/cover.png") 
        print("✅ Created cover image: agentic-ai-cover.png")
    else:
        # Create SVG cover
        svg_cover = '''<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="coverGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
        </linearGradient>
    </defs>
    <rect width="1200" height="630" fill="url(#coverGrad)"/>
    
    <text x="600" y="200" text-anchor="middle" fill="white" font-family="Arial" font-size="72" font-weight="bold">🧠 Agentic AI System</text>
    <text x="600" y="280" text-anchor="middle" fill="white" font-family="Arial" font-size="36" opacity="0.9">Autonomous Multi-Agent Intelligence with Voice Interaction</text>
    
    <text x="600" y="340" text-anchor="middle" fill="white" font-family="Arial" font-size="24" opacity="0.8">✨ 20+ Specialized AI Agents</text>
    <text x="600" y="380" text-anchor="middle" fill="white" font-family="Arial" font-size="24" opacity="0.8">🎤 Advanced Voice Interaction</text>
    <text x="600" y="420" text-anchor="middle" fill="white" font-family="Arial" font-size="24" opacity="0.8">📱 Progressive Web App (PWA)</text>
    <text x="600" y="460" text-anchor="middle" fill="white" font-family="Arial" font-size="24" opacity="0.8">🚀 Auto-Deploy to Multiple Platforms</text>
    <text x="600" y="500" text-anchor="middle" fill="white" font-family="Arial" font-size="24" opacity="0.8">🔄 Real-time Agent Creation</text>
    
    <text x="600" y="580" text-anchor="middle" fill="white" font-family="Arial" font-size="20" opacity="0.7">🇮🇩 Made with ❤️ by Mulky Malikul Dhaher in Indonesia</text>
</svg>'''
        
        with open("agentic-ai-cover.svg", 'w') as f:
            f.write(svg_cover)
        
        with open("web_interface/static/cover.svg", 'w') as f:
            f.write(svg_cover)
        
        print("✅ Created SVG cover image: agentic-ai-cover.svg")

# Icon sizes for PWA
icon_sizes = [
    (16, "icon-16x16.png"),
    (32, "icon-32x32.png"), 
    (72, "icon-72x72.png"),
    (96, "icon-96x96.png"),
    (128, "icon-128x128.png"),
    (144, "icon-144x144.png"),
    (152, "icon-152x152.png"),
    (180, "icon-180x180.png"),
    (192, "icon-192x192.png"),
    (384, "icon-384x384.png"),
    (512, "icon-512x512.png")
]

print("🎨 Creating Agentic AI System icons and cover...")

# Create all icons
for size, filename in icon_sizes:
    create_icon(size, filename)

# Create additional icons
create_icon(96, "voice-icon.png")
create_icon(96, "agent-icon.png") 
create_icon(96, "code-icon.png")
create_icon(72, "badge-72x72.png")

# Create cover image
create_cover_image()

print("\n🎉 All icons and cover image created successfully!")
print("📁 Icons location: web_interface/static/icons/")
print("🖼️  Cover image: agentic-ai-cover.png")
print("🇮🇩 Made with ❤️ by Mulky Malikul Dhaher in Indonesia")
