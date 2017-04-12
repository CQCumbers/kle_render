#!/Users/alexanderzhang/Envs/kle_render/bin/python3.5
#
# The Python Imaging Library
# $Id$
#
# this demo script illustrates pasting into an already displayed
# photoimage.  note that the current version of Tk updates the whole
# image every time we paste, so to get decent performance, we split
# the image into a set of tiles.
#

import sys

if sys.version_info[0] > 2:
    import tkinter
else:
    import Tkinter as tkinter

from PIL import Image, ImageTk

#
# painter widget


class PaintCanvas(tkinter.Canvas):
    def __init__(self, master, image):
        tkinter.Canvas.__init__(self, master,
                                width=image.size[0], height=image.size[1])

        # fill the canvas
        self.tile = {}
        self.tilesize = tilesize = 32
        xsize, ysize = image.size
        for x in range(0, xsize, tilesize):
            for y in range(0, ysize, tilesize):
                box = x, y, min(xsize, x+tilesize), min(ysize, y+tilesize)
                tile = ImageTk.PhotoImage(image.crop(box))
                self.create_image(x, y, image=tile, anchor=tkinter.NW)
                self.tile[(x, y)] = box, tile

        self.image = image

        self.bind("<B1-Motion>", self.paint)

    def paint(self, event):
        xy = event.x - 10, event.y - 10, event.x + 10, event.y + 10
        im = self.image.crop(xy)

        # process the image in some fashion
        im = im.convert("L")

        self.image.paste(im, xy)
        self.repair(xy)

    def repair(self, box):
        # update canvas
        dx = box[0] % self.tilesize
        dy = box[1] % self.tilesize
        for x in range(box[0]-dx, box[2]+1, self.tilesize):
            for y in range(box[1]-dy, box[3]+1, self.tilesize):
                try:
                    xy, tile = self.tile[(x, y)]
                    tile.paste(self.image.crop(xy))
                except KeyError:
                    pass  # outside the image
        self.update_idletasks()

#
# main

if len(sys.argv) != 2:
    print("Usage: painter file")
    sys.exit(1)

root = tkinter.Tk()

im = Image.open(sys.argv[1])

if im.mode != "RGB":
    im = im.convert("RGB")

PaintCanvas(root, im).pack()

root.mainloop()
