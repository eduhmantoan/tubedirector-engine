#!/usr/bin/env python3
"""Generate deterministic brand-inspired icons for Tauri installers.

Requirements: Pillow. On macOS, Apple's iconutil (part of Xcode command line tools).
No stock/downloaded icons are used; assets are derived from geometric shapes.
"""
from pathlib import Path
import math
import platform
import subprocess
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src-tauri/icons"
OUT.mkdir(parents=True, exist_ok=True)
S = 1024
im = Image.new("RGBA", (S, S), (0,0,0,0))
d = ImageDraw.Draw(im)
for inset in range(0, 180):
    k = inset / 180
    color = (int(17 + 28*k), int(35 + 22*k), int(97 + 86*k), max(0, int(255*(1-k)**1.6)))
    d.rounded_rectangle((inset, inset, S-inset-1, S-inset-1), radius=245-inset//3, fill=color)
# Main icon's luminous glass base.
for inset in range(85, 155):
    t=(inset-85)/70
    d.rounded_rectangle((inset,inset,S-inset,S-inset),radius=210-inset//6,fill=(24,int(150-55*t),int(246-40*t),int(180-100*t)))
# Signature TubeDirector play triangle and orbital wave.
halo=Image.new("RGBA",(S,S),(0,0,0,0))
h=ImageDraw.Draw(halo)
h.arc((170,185,855,830),210,345,fill=(220,75,255,235),width=34)
h.arc((170,185,855,830),24,168,fill=(40,221,255,225),width=28)
blur=halo.filter(ImageFilter.GaussianBlur(40))
im=Image.alpha_composite(im,blur)
im=Image.alpha_composite(im,halo)
d=ImageDraw.Draw(im)
d.rounded_rectangle((235,235,795,795),radius=135,fill=(10,20,65,230),outline=(118,195,255,240),width=10)
d.polygon([(408,344),(408,687),(703,515)],fill=(33,213,248,255))
d.polygon([(449,395),(449,636),(649,515)],fill=(205,79,255,255))
im.save(OUT/"icon.png")
im.resize((128,128),Image.Resampling.LANCZOS).save(OUT/"128x128.png")
im.resize((32,32),Image.Resampling.LANCZOS).save(OUT/"32x32.png")
im.save(OUT/"icon.ico",sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
if platform.system()=="Darwin":
    iconset=OUT/"TubeDirector.iconset"
    iconset.mkdir(exist_ok=True)
    for size in (16,32,128,256,512):
        for mult in (1,2):
            name=f"icon_{size}x{size}" + ("@2x" if mult==2 else "") + ".png"
            im.resize((size*mult,size*mult),Image.Resampling.LANCZOS).save(iconset/name)
    subprocess.run(["iconutil","-c","icns",str(iconset),"-o",str(OUT/"icon.icns")],check=True)
else:
    # The configured bundle contains icon.icns even on Windows; keep a valid generated
    # ICNS file so bundler resource checks do not fail on cross-platform builds.
    im.save(OUT/"icon.icns", format="ICNS")
print("Assets gerados em", OUT)
