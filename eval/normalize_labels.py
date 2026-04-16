import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "eval" / "labeled_dataset.json"
OUTPUT_FILE = PROJECT_ROOT / "eval" / "labeled_dataset_normalized.json"


def simplify_garment(s: str | None) -> str | None:
    if not s:
        return s
    s = s.lower()

    special = {
        "striped t-shirt, wide-leg trousers, sneakers": "t-shirt",
        "denim jacket, crop top, straight-leg trousers": "jacket",
        "striped blazer, camisole, trousers": "blazer",
        "peplum top, wide-leg pants": "top",
        "oversized blazer, turtleneck top, trousers": "blazer",
        "graphic t-shirt, wide-leg trousers": "t-shirt",
        "double-breasted blazer, tank top, trousers": "blazer",
        "printed matching shirt, printed trousers, boots": "shirt",
        "crop top, baggy jeans, cardigan": "jeans",
        "faux fur jacket, t-shirt, jeans": "jacket",
        "cropped denim jacket, fitted top, jeans": "jacket",
        "oversized shirt, mini skirt": "shirt",
        "hoodie, denim jacket": "hoodie",
        "oversized leather jacket, top, trousers": "jacket",
        "embroidered dress, draped outer layer": "dress",
        "jumpsuit": "jumpsuit",
        "traditional blouse, full skirt, hat": "skirt",
        "ruffled mini dress, sheer train": "dress",
        "textured statement coat": "coat",
        "cropped shirt, mini skirt, scarf": "shirt",
        "satin blouse, high-waist trousers": "blouse",
        "embroidered cardigan, inner top": "cardigan",
        "wedding gown": "dress",
        "ballet dress, tights": "dress",
        "cropped jacket, knit top, houndstooth skirt": "jacket",
        "traditional blouse, skirt, shawl": "skirt",
        "graphic t-shirt, tights, heels": "t-shirt",
        "blouson jacket, slip skirt, tights": "jacket",
        "deconstructed blazer, midi skirt": "blazer",
        "corset gown": "dress",
        "crop top, blazer, trousers": "blazer",
        "cargo shirt, wide-leg cargo pants": "shirt",
        "embroidered coat": "coat",
        "collared mini dress": "dress",
        "embellished jacket, wide-leg trousers": "jacket",
        "printed matching set": "set",
        "embellished shawl, floral skirt, boots": "skirt",
        "utility jumpsuit, oversized blouse, wide-leg pants": "jumpsuit",
        "wedding dress, veil": "dress",
        "denim jacket, sweater vest, wide-leg trousers": "jacket",
        "metallic jacket, fitted top, cargo pants": "jacket",
        "striped t-shirt": "t-shirt",
        "crop top, distressed jeans, beanie": "jeans",
        "wool coat, mini dress, beret": "coat",
        "pinstripe blazer, mini skirt, top": "blazer",
        "colorblock tunic, trousers": "tunic",
    }
    return special.get(s, s.split(",")[0].strip())


def simplify_style(s: str | None) -> str | None:
    if not s:
        return s
    s = s.lower()
    return {
        "smart-casual": "casual",
        "bridal": "formal",
    }.get(s, s)


def simplify_material(s: str | None) -> str | None:
    if not s:
        return s
    s = s.lower()
    mapping = {
        "cotton blend": "cotton",
        "wool blend": "wool",
        "synthetic blend": "synthetic",
        "cotton knit": "cotton",
        "faux fur, cotton, denim": "synthetic",
        "denim, cotton": "denim",
        "cotton, satin": "cotton",
        "cotton, denim": "cotton",
        "faux leather, cotton": "synthetic",
        "silk blend": "silk",
        "tulle, chiffon": "tulle",
        "cotton blend, knit": "cotton",
        "satin, cotton blend": "satin",
        "knit, cotton": "knit",
        "chiffon, tulle": "chiffon",
        "tulle, knit": "tulle",
        "denim, knit, tweed": "denim",
        "cotton, wool blend": "cotton",
        "cotton, sheer knit": "cotton",
        "nylon, lace, sheer": "nylon",
        "denim, wool blend": "denim",
        "mesh, satin": "mesh",
        "cotton, wool blend": "cotton",
        "jacquard, satin": "jacquard",
        "cotton, rope embellishment": "cotton",
        "satin blend": "satin",
        "knit, chiffon, leather": "knit",
        "cotton twill": "cotton",
        "denim, wool blend, cotton": "denim",
        "nylon, cotton": "nylon",
        "wool, satin": "wool",
        "wool blend, cotton": "wool",
    }
    return mapping.get(s, s.split(",")[0].strip().split()[0])


def simplify_occasion(s: str | None) -> str | None:
    if not s:
        return s
    s = s.lower()
    return {
        "workwear": "formal",
    }.get(s, s)


with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

out = []
for item in data:
    exp = item["expected"].copy()
    exp["garment_type"] = simplify_garment(exp.get("garment_type"))
    exp["style"] = simplify_style(exp.get("style"))
    exp["material"] = simplify_material(exp.get("material"))
    exp["occasion"] = simplify_occasion(exp.get("occasion"))
    out.append({
        "filename": item["filename"],
        "expected": exp
    })

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print(f"Saved: {OUTPUT_FILE}")