"""Create a disposable, non-square TGA for pointer/import QA (never packaged)."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw

target = Path(sys.argv[1])
target.parent.mkdir(parents=True, exist_ok=True)
width = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
height = int(sys.argv[3]) if len(sys.argv) > 3 else 512
image = Image.new('RGB', (width, height), '#e04040')
draw = ImageDraw.Draw(image)
draw.rectangle((width//2, 0, width-1, height//2-1), fill='#40c080')
draw.rectangle((0, height//2, width//2-1, height-1), fill='#4080e0')
draw.rectangle((width//2, height//2, width-1, height-1), fill='#e0c040')
for x, y in [(width//4,height//4),(3*width//4,height//4),(width//4,3*height//4),(3*width//4,3*height//4)]:
    draw.line((x-20,y,x+20,y), fill='white', width=3)
    draw.line((x,y-20,x,y+20), fill='white', width=3)
image.save(target, 'TGA')
print(target)
