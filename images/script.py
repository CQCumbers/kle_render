from PIL import Image, ImageDraw
import os

u = 200
#transparent_area = (0,u,int(0.25*u),int(2*u))
transparent_area = (0, 0, int(0.75*u), u)

for fn in os.listdir('.'):
     #if os.path.isfile(fn) and fn.startswith('SA_ISO'):
     #if os.path.isfile(fn) and fn.startswith('SA_BIGENTER'):
     if os.path.isfile(fn) and fn.endswith('crunch.png'):
        im = Image.open(fn)
        im.save(fn[:-11]+'.png')

        #im = Image.open(fn)
        #mask=Image.new('L', im.size, color=255)
        #draw=ImageDraw.Draw(mask) 
        #draw.rectangle(transparent_area, fill=0)
        #im.putalpha(mask)
        #im.save(fn[:-4]+'.png')
