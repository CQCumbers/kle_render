from PIL import Image, ImageMath, ImageColor, ImageCms, ImageDraw, ImageFont
from colormath.color_objects import LabColor, sRGBColor
from colormath.color_conversions import convert_color
import math, textwrap

srgb_profile = ImageCms.createProfile('sRGB')
lab_profile = ImageCms.createProfile('LAB')
rgb2lab_transform = ImageCms.buildTransformFromOpenProfiles(srgb_profile, lab_profile, 'RGB', 'LAB')
lab2rgb_transform = ImageCms.buildTransformFromOpenProfiles(lab_profile, srgb_profile, 'LAB', 'RGB')

GMK_LABELS = ('GMK', 'DCS', 'OEM')

# Key and deserialise() modified from https://github.com/jackhumbert/kle-image-creator
class Key(object):
    __slots__ = ['u', 'base_color', 'x', 'y', 'x2', 'y2', 'width', 'height', 'width2', 'height2', 'color', 'font_color', 'labels', 'align', 'font_size', 'font_size2', 'rotation_angle', 'rotation_x', 'rotation_y', 'profile', 'nub', 'ghost', 'stepped', 'decal']

    def __init__(self):

        self.u = 200
        self.base_color = 0xE0

        self.x = 0.0
        self.y = 0.0
        self.x2 =0.0
        self.y2 = 0.0
        self.width = 1.0
        self.height = 1.0
        self.width2 = 1.0
        self.height2 = 1.0
        self.color = '#EEEEEE'
        self.font_color = '#000000'
        self.labels =[]
        self.align = 0
        self.font_size = 3.0
        self.font_size2 = 3.0
        self.rotation_angle = 0.0
        self.rotation_x = 0.0
        self.rotation_y = 0.0
        self.profile = ''
        self.nub = False
        self.ghost = False
        self.stepped = False
        self.decal = False

    def font_path(self):
        if self.profile in ['DCS', 'OEM', 'GMK']:
            return 'CherryRounded.otf'
        else:
            return 'NotoRounded.otf'

    def get_base_img(self):
        if self.profile in ['DCS', 'OEM', 'GMK']: # GMK technically not supported by KLE yet
            return Image.open(r'GMK_Base.jpg').convert('RGBA') # GMK photo from official renders
        elif 'SPACE' in self.profile:
            color = ImageColor.getrgb(self.color)
            bright = 0.3*color[0] + 0.59*color[1] + 0.11*color[2]
            if (bright > 0x50):
                base_num = '1'
            else:
                base_num = '2'
            return Image.open('SA_Space_Base{}.jpg'.format(base_num)).convert('RGBA') # SA renders by me
        else:
            color = ImageColor.getrgb(self.color)
            bright = 0.3*color[0] + 0.59*color[1] + 0.11*color[2]
            if (bright > 0xB0):
                base_num = '1'
            elif (bright > 0x80):
               base_num = '2'
            elif (bright > 0x50):
                base_num = '3'
            elif (bright > 0x20):
                base_num = '4'
            else:
                base_num = '5'
            return Image.open('SA_Base{}.jpg'.format(base_num)).convert('RGBA') # SA renders by me

    def get_base_color(self):
        if self.profile in ['DCS', 'OEM', 'GMK']: # GMK technically not supported by KLE yet
            return 0xE0
        elif 'SPACE' in self.profile:
            color = ImageColor.getrgb(self.color)
            bright = 0.3*color[0] + 0.59*color[1] + 0.11*color[2]
            if (bright > 0x50):
                return 0xE0
            else:
                return 0x50
        else:
            color = ImageColor.getrgb(self.color)
            bright = 0.3*color[0] + 0.59*color[1] + 0.11*color[2] # Perceptual gray
            if (bright > 0xB0):
                return 0xE0
            elif (bright > 0x80):
                return 0xB0
            elif (bright > 0x50):
                return 0x80
            elif (bright > 0x20):
                return 0x50
            else:
                return 0x20

    def location(self, key_img): # get pixel location of key as (left, upper, right, lower)
        u = self.u
        x, y = self.x, self.y
        if self.rotation_angle != 0:
            rx, ry = self.rotation_x, self.rotation_y # center about which to rotate key
            a = self.rotation_angle * math.pi / 180
            x2, y2 = x*math.cos(a) - y*math.sin(a), y*math.cos(a) + x*math.sin(a)

            left, top = -self.width/2, -self.height/2
            left2, top2 = left*math.cos(a) - top*math.sin(a), top*math.cos(a) + left*math.sin(a)

            x, y = rx + x2 - key_img.width/u/2 - left2, ry + y2 - key_img.height/u/2 - top2
        return (int(x*u), int(y*u), int(x*u + key_img.width), int(y*u + key_img.height))

    def tint_key(self, key_img): #a image of the key, and a hex color code string
        alpha = key_img.split()[3]
        key_img = ImageCms.applyTransform(key_img, rgb2lab_transform)
        l, a, b = key_img.split()
        rgb_color = sRGBColor(*ImageColor.getrgb(self.color), is_upscaled=True)
        lab_color = convert_color(rgb_color, LabColor)

        l1, a1, b1 = [int(i) for i in lab_color.get_value_tuple()]
        l1 = int(l1*255/100)
        l = ImageMath.eval('l2 - l3 + l1', l2=l, l3=self.base_color, l1=l1).convert('L')
        a = ImageMath.eval('a2 + a1', a2=a, a1=a1, l2=l).convert('L')
        b = ImageMath.eval('b2 + b1', b2=b, b1=b1, l2=l).convert('L')

        key_img = Image.merge('LAB', (l, a, b))
        key_img = ImageCms.applyTransform(key_img, lab2rgb_transform)
        key_img = Image.merge('RGBA', (*key_img.split(), alpha))
        return key_img

    def stretch_key(self): # width and height of key in units
        base_img = self.get_base_img()
        u = self.u
        width, height = int(self.width*u)+1, int(self.height*u)+1 # Width & Height of image representing key
        key_img = Image.new('RGBA', (width, height)) # Lots of +1s to avoid unsightly gaps between keys
        key_img.paste(base_img, (0, 0, u, u))
        if width != u:
            center_part = base_img.crop((int(u/2), 0, int(u/2)+1, u)) # horizontal middle strip of image
            right_part = base_img.crop((int(u/2)+1, 0, u, u))
            for i in range(width - u + 1):
                key_img.paste(center_part, (int(u/2) + i, 0, int(u/2) + i + 1, u))
            key_img.paste(right_part, (width - right_part.width, 0, width, u))
        if height != u:
            middle_part = key_img.crop((0, int(u/2), width, int(u/2)+1)) # vertical middle strip of image
            bottom_part = key_img.crop((0, int(u/2)+1, width, u))
            for i in range(height - u + 1):
                key_img.paste(middle_part, (0, int(u/2) + i, key_img.width, int(u/2) + i + 1))
            key_img.paste(bottom_part, (0, height - bottom_part.height, width, height))
        return key_img

    def decal_key(self):
        scale_factor = 8
        min_size = 8
        line_spacing = 16
        labels = [text.upper() for text in self.labels] # only uppercase text on SA

        gotham = ImageFont.truetype(self.font_path(), int(self.font_size*scale_factor)+min_size)
        w = max([gotham.getsize(text)[0] for text in labels]) # max of widths
        h = sum([gotham.getsize(text)[1] for text in labels]) # sum of heights
        h += line_spacing*(len([text for text in labels if len(text) > 0])-1)

        key_img = Image.new('RGBA', (w+64, h+108))
        return key_img

    def text_key(self, key_img):
        labels = self.labels
        #labels = [labels[i] for i in range(len(labels)) if len(labels[i]) > 0 and '</i>' not in labels[i] and i not in (4,5)] # ignore blank lines, html, and labels on front (not top) of key
        if len(labels) <= 0:
            return key_img # if blank, exit immediately
        else:
            if self.decal:
                offset = 0  # pixels to shift text upwards to center it in keycap top
                scale_factor = 7 # multiply this by the legend size and add to min_size to get font size for that legend
                min_size = 16
                line_spacing = 16 # space between lines (only matters for <= 2 labels)
                width_limit = key_img.width # maximum line width in pixels before automatic line break (Only matters for 1 label)
            elif self.profile.startswith(GMK_LABELS):
                offset = 12
                scale_factor = 9
                min_size = 12
                line_spacing = 12
                width_limit = key_img.width - 55
            else:
                offset = 12
                scale_factor = 7
                min_size = 16
                line_spacing = 16
                width_limit = key_img.width - 42
                labels = [labels[i].upper() for i in range(len(labels))] # Only uppercase legends on SA keycaps

            font = ImageFont.truetype(self.font_path(), int(self.font_size*scale_factor)+min_size)
            draw = ImageDraw.Draw(key_img)
            c = ImageColor.getrgb(self.font_color)
            c = tuple(band + 0x26 for band in c) # Simulates reflectivity 

            if len(labels) <= 2 and labels[0] != '': # If 2 or fewer labels, center accurately depending on profile
                if self.profile.startswith(GMK_LABELS):
                    draw.multiline_text((45, 45-offset), '\n'.join(labels), font=font, fill=c, spacing=line_spacing)
                else:
                    w = max([font.getsize(text)[0] for text in labels]) # max of label widths
                    if len(labels) == 1 and w > width_limit and not self.decal: # wrap text only for single labels
                        labels = [line for label in labels for line in textwrap.wrap(label, width=int(width_limit/(font.getsize('L')[0])))]
                        w = max([font.getsize(text)[0] for text in labels])
                    h = sum([font.getsize(text)[1] for text in labels]) # sum of heights
                    h += line_spacing*(len([text for text in labels])-1)
                    draw.multiline_text((int((key_img.width-w)/2), int((key_img.height-h)/2 - offset)), '\n'.join(labels), font=font, fill=c, spacing=line_spacing, align='center')
            else: # Otherwise copy keyboard layout editor legend positions
                alignments = [[1, 9, 3, 7, 10, 8, 2, 11, 4, 5, 12, 6],
                            [-1, 1, -1, -1, 7, -1, -1, 2, -1, 5, 12, 6],
                            [-1, -1, -1, 1, 9, 3, -1, -1, -1, 5, 12, 6],
                            [-1, -1, -1, -1, 1, -1, -1, -1, -1, 5, 12, 6],
                            [1, 9, 3, 7, 10, 8, 2, 11, 4, -1, 5, -1],
                            [-1, 1, -1, -1, 7, -1, -1, 2, -1, -1, 5, -1],
                            [-1, -1, -1, 1, 9, 3, -1, -1, -1, -1, 5, -1],
                            [-1, -1, -1, -1, 1, -1, -1, -1, -1, -1, 5, -1]]
                align = [i-1 for i in alignments[self.align]]

                for i in range(len(labels)):
                    text = labels[i]
                    if i == align[0]:
                        draw.text((45, 45-offset), text, font=font, fill=c)
                    elif i == align[6]:
                        h = font.getsize(text)[1]
                        draw.text((45, key_img.height-45-h-offset), text, font=font, fill=c)
                    elif i == align[2]:
                        w = font.getsize(text)[0]
                        draw.text((key_img.width-45-w, 45-offset), text, font=font, fill=c)
                    elif i == align[8]:
                        w = font.getsize(text)[0]
                        h = font.getsize(text)[1]
                        draw.text((key_img.width-45-w, key_img.height-45-h-offset), text, font=font, fill=c)
                    elif i == align[3]:
                        h = font.getsize(text)[1]
                        draw.text((45, (key_img.height-h)/2-offset), text, font=font, fill=c)
                    elif i == align[5]:
                        w = font.getsize(text)[0]
                        h = font.getsize(text)[1]
                        draw.text((key_img.width-45-w, (key_img.height-h)/2-offset), text, font=font, fill=c)
                    elif i == align[1]:
                        w = font.getsize(text)[0]
                        draw.text(((key_img.width-w)/2, 45-offset), text, font=font, fill=c)
                    elif i == align[4]:
                        w = font.getsize(text)[0]
                        h = font.getsize(text)[1]
                        draw.text(((key_img.width-w)/2, (key_img.height-h)/2-offset), text, font=font, fill=c)
                    elif i == align[7]:
                        w = font.getsize(text)[0]
                        h = font.getsize(text)[1]
                        draw.text(((key_img.width-w)/2, key_img.height-45-h-offset), text, font=font, fill=c)

            return key_img 

    def render(self):
        self.base_color = self.get_base_color()

        if self.decal:
            key_img = self.decal_key()
        else:
            key_img = self.stretch_key()
            key_img = self.tint_key(key_img)
        key_img = self.text_key(key_img)
        if self.rotation_angle != 0:
            key_img = key_img.resize(tuple(i+2 for i in key_img.size))
            key_img = key_img.rotate(-self.rotation_angle, resample=Image.BICUBIC, expand=1)
        return key_img
