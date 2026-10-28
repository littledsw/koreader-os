#!/usr/bin/env python3
"""从 iNaturalist 抓 CC 授权动物照片，处理成 16 灰阶，供图鉴使用。"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance

OUT = Path("assets/animals"); OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0"
SPECIES = [
    ("giant-panda", "Ailuropoda melanoleuca"),
    ("chinese-pangolin", "Manis pentadactyla"),
    ("crested-ibis", "Nipponia nippon"),
]

def get(url, out):
    r = subprocess.run(["curl","-sSL","-m","90","-A",UA,url,"-o",str(out),"-w","%{http_code}"],
                       capture_output=True, text=True)
    return r.stdout.strip() == "200"

credits = {}
for slug, name in SPECIES:
    q = (f"https://api.inaturalist.org/v1/observations?taxon_name={name.replace(' ','%20')}"
         "&photos=true&per_page=3&license=cc0,cc-by&quality_grade=research"
         "&fields=id,observed_on,photos,user")
    tmp = Path("/tmp")/f"{slug}.json"
    if not get(q, tmp):
        print("query failed", slug); continue
    try:
        data = json.loads(tmp.read_text())
    except Exception as e:
        print("json fail", slug, e); continue
    picked = None
    for o in data.get("results", []):
        for p in o.get("photos", []):
            if p.get("license_code") in ("cc0","cc-by"):
                picked = (o, p); break
        if picked: break
    if not picked:
        print("no photo", slug); continue
    o, p = picked
    url = p["url"].replace("/square.", "/original.")
    raw = Path("/tmp")/f"{slug}_raw.jpg"
    if not get(url, raw):
        print("download failed", slug); continue
    im = Image.open(raw).convert("L")
    im = ImageOps.exif_transpose(im)
    w, h = im.size
    # 按 3:2 居中裁切
    tw, th = (w, int(w*2/3)) if w/h >= 1.5 else (int(h*1.5), h)
    left, top = (w-tw)//2, (h-th)//2
    im = im.crop((left, top, left+tw, top+th)).resize((960, 640), Image.LANCZOS)
    im = ImageOps.autocontrast(im, cutoff=1)
    im = ImageEnhance.Contrast(im).enhance(1.08)
    dest = OUT/f"{slug}.png"
    im.save(dest)
    credits[slug] = {"scientific": name, "license": p.get("license_code"),
                     "by": (o.get("user") or {}).get("login", ""),
                     "observed_on": o.get("observed_on"), "file": str(dest)}
    print("ok", slug, dest, im.size, p.get("license_code"), credits[slug]["by"])

(OUT/"CREDITS.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2), encoding="utf-8")
print("done", len(credits))
