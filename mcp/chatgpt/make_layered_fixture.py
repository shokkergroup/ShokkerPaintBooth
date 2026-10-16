"""Small explicit layered acceptance artwork, never a customer's template."""
from pathlib import Path
from io import BytesIO
import hashlib
import json
import zipfile
from xml.etree.ElementTree import Element, SubElement, tostring
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / '_release_evidence/chatgpt-dev/59910/fixtures'
DEST.mkdir(parents=True, exist_ok=True)
SIZE = (512, 512)
NAVY = (25, 55, 110, 255)
body = Image.new('RGBA', SIZE, NAVY)
number = Image.new('RGBA', SIZE)
d = ImageDraw.Draw(number)
font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 144)
d.text((50, 214), '32', font=font, fill=NAVY, stroke_width=9, stroke_fill=(255,255,255,255))
sponsor = Image.new('RGBA', SIZE)
d = ImageDraw.Draw(sponsor)
d.rounded_rectangle((246,58,452,126), radius=8, fill=NAVY, outline=(255,190,35,255), width=6)
d.text((286,64), 'SPB', font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 44), fill=(255,255,255,255))
layers = [('Sponsors', sponsor), ('Numbers', number), ('Body', body)]
composite = body.copy()
for _, layer in reversed(layers[:-1]):
    composite = Image.alpha_composite(composite, layer)
def png(image):
    out = BytesIO(); image.save(out, format='PNG'); return out.getvalue()
image = Element('image', {'w':'512','h':'512','name':'Private layered protection acceptance'})
stack = SubElement(image, 'stack')
archive = DEST / 'layered-protection-a.ora'
with zipfile.ZipFile(archive, 'w') as z:
    z.writestr('mimetype', 'image/openraster', compress_type=zipfile.ZIP_STORED)
    for i, (name, layer) in enumerate(layers):
        entry = f'data/layer{i}.png'
        z.writestr(entry, png(layer), compress_type=zipfile.ZIP_DEFLATED)
        SubElement(stack, 'layer', {'name':name,'src':entry,'x':'0','y':'0','opacity':'1.0','visibility':'visible','composite-op':'svg:src-over'})
    z.writestr('stack.xml', tostring(image, encoding='utf-8', xml_declaration=True))
    z.writestr('mergedimage.png', png(composite))
    thumb = composite.copy(); thumb.thumbnail((256,256)); z.writestr('Thumbnails/thumbnail.png', png(thumb))
records = []
for name, layer in layers:
    file = DEST / ('layered-protection-a-' + name.lower() + '.png')
    file.write_bytes(png(layer))
    records.append({'name':name,'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'role':'body' if name=='Body' else 'protected artwork','contains_body_navy':True})
flat = DEST / 'layered-protection-a-composite.png'; flat.write_bytes(png(composite))
manifest = {'scope':'Synthetic 512x512 layer-protection fixture; no car layout or real customer artwork','archive':archive.name,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'composite':flat.name,'composite_sha256':hashlib.sha256(flat.read_bytes()).hexdigest(),'layer_order_top_to_bottom':records,'font':'Windows Arial Bold','body_rgba':NAVY}
(DEST / 'layered-protection-a.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'archive':str(archive),'layers':[r['name'] for r in records],'size':SIZE}))
