#!/usr/bin/env python3
"""抓候选照片，拼成对比图，供挑选。"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

OUT = Path("assets/candidates"); OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0"
name = sys.argv[1]; slug = sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 8

q = (f"https://api.inaturalist.org/v1/observations?taxon_name={name.replace(' ','+')}"
     "&photos=true&per_page=%d&license=cc0,cc-by&quality_grade=research"
     "&fields=id,observed_on,photos,user" % n)
tmp = Path("/tmp")/f"{slug}.json"
subprocess.run(["curl","-sSL","-m","240","-A",UA,q,"-o",str(tmp)])
data = json.loads(tmp.read_text())

thumbs = []
for i, o in enumerate(data.get("results", [])):
    if not o.get("photos"): continue
    p = o["photos"][0]
    url = p["url"].replace("/square.", "/large.")
    raw = Path("/tmp")/f"{slug}_{i}.jpg"
    r = subprocess.run(["curl","-sSL","-m","240","-A",UA,url,"-o",str(raw),"-w","%{http_code}"],
                       capture_output=True, text=True)
    if r.stdout.strip() != "200": continue
    im = Image.open(raw).convert("L")
    im = ImageOps.exif_transpose(im)
    im.thumbnail((380, 380), Image.LANCZOS)
    canvas = Image.new("L", (380, 380), 240)
    canvas.paste(im, ((380-im.width)//2, (380-im.height)//2))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0,0,60,26], fill=0); d.text((8,6), str(i), fill=255)
    thumbs.append(canvas)

cols = 4; rows = (len(thumbs)+cols-1)//cols
sheet = Image.new("L", (cols*390, rows*390), 200)
for k, t in enumerate(thumbs):
    r_, c_ = divmod(k, cols)
    sheet.paste(t, (c_*390+5, r_*390+5))
path = OUT/f"{slug}_sheet.png"; sheet.save(path)
print(path, sheet.size, len(thumbs))
