from PIL import Image, ImageMath, ImageColor, ImageCms, ImageDraw, ImageFont
from colormath.color_objects import LabColor, sRGBColor
from colormath.color_conversions import convert_color
import math, textwrap

# Key and deserialise() modified from https://github.com/jackhumbert/kle-image-creator
class Key(object):
    font_path = r'NotoRounded.otf'

    def __init__(self):
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
        self.align = 4
        self.font_size = 8.0
        self.font_size2 = 8.0
        self.rotation_angle = 0.0
        self.rotation_x = 0.0
        self.rotation_y = 0.0
        self.profile = ''
        self.nub = False
        self.ghost = False
        self.stepped = False
        self.decal = False

    def base_img(self):
        if self.profile in ['DCS', 'OEM', 'GMK']: # GMK technically not supported by KLE yet
            return Image.open(r'GMK_base.jpg').convert('RGBA').resize((200, 200)) # GMK photo from official renders
        elif self.profile in ['SA SPACE']:
            color = ImageColor.getrgb(self.color)
            bright = 0.3*color[0] + 0.59*color[1] + 0.11*color[2]
            if (bright > 0x50):
                base_num = '1'
            else:
                base_num = '2'
            return Image.open('SA_Space_Base{}.jpg'.format(base_num)).convert('RGBA').resize((200, 200)) # SA renders by me
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
            return Image.open('SA_Base{}.jpg'.format(base_num)).convert('RGBA').resize((200, 200)) # SA renders by me

    def base_color(self):
        if self.profile in ['DCS', 'OEM', 'GMK']: # GMK technically not supported by KLE yet
            return 0xE0
        elif self.profile in ['SA SPACE']:
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

    def u(self):
        return self.base_img().width

    def location(self, key_img): # get pixel location of key as (left, upper, right, lower)
        u = self.u()
        x, y = self.x, self.y
        if self.rotation_angle != 0:
            rx, ry = self.rotation_x, self.rotation_y # center about which to rotate key
            a = self.rotation_angle * math.pi / 180
            x2, y2 = x*math.cos(a) - y*math.sin(a), y*math.cos(a) + x*math.sin(a)

            left, top = -self.width/2, -self.height/2
            left2, top2 = left*math.cos(a) - top*math.sin(a), top*math.cos(a) + left*math.sin(a)

            x, y = rx + x2 - key_img.width/u/2 - left2, ry + y2 - key_img.height/u/2 - top2
        return (int(x*u), int(y*u), int(x*u + key_img.width), int(y*u + key_img.height))

    def rough_location(self): # not accurate - assumes no rotations, but doesn't require rendering
        u = self.u()
        x, y = self.x, self.y
        return (int(x*u), int(y*u), int(x*u + self.width*u), int(y*u + self.height*u))

    def tint_key(self, key_img): #a image of the key, and a hex color code string
        srgb_profile = ImageCms.createProfile('sRGB')
        lab_profile = ImageCms.createProfile('LAB')
        rgb2lab_transform = ImageCms.buildTransformFromOpenProfiles(srgb_profile, lab_profile, 'RGB', 'LAB')
        lab2rgb_transform = ImageCms.buildTransformFromOpenProfiles(lab_profile, srgb_profile, 'LAB', 'RGB')

        alpha = key_img.split()[3]
        key_img = ImageCms.applyTransform(key_img, rgb2lab_transform)
        l, a, b = key_img.split()
        rgb_color = sRGBColor(*ImageColor.getrgb(self.color), is_upscaled=True)
        lab_color = convert_color(rgb_color, LabColor)

        l1, a1, b1 = int(lab_color.get_value_tuple()[0]*255/100), int(lab_color.get_value_tuple()[1]), int(lab_color.get_value_tuple()[2])
        l = ImageMath.eval('l2 - l3 + l1', l2=l, l3=self.base_color(), l1=l1).convert('L')
        a = ImageMath.eval('a2 + a1', a2=a, a1=a1).convert('L')
        b = ImageMath.eval('b2 + b1', b2=b, b1=b1).convert('L')

        key_img = Image.merge('LAB', (l, a, b))
        key_img = ImageCms.applyTransform(key_img, lab2rgb_transform)
        key_img = Image.merge('RGBA', (*key_img.split(), alpha))
        return key_img

    def stretch_key(self): # width and height of key in units
        base_img = self.base_img()
        u = self.u()
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

        gotham = ImageFont.truetype(self.font_path, int(self.font_size*scale_factor)+min_size)
        w = max([gotham.getsize(text)[0] for text in labels]) # max of widths
        h = sum([gotham.getsize(text)[1] for text in labels]) # sum of heights
        h += line_spacing*(len([text for text in labels if len(text) > 0])-1)

        key_img = Image.new('RGBA', (w+24, h+108))
        return key_img

    def text_key(self, key_img): # convert for use with list of labels
        labels = self.labels
        labels = [labels[i].upper() for i in range(len(labels)) if len(labels[i]) > 0 and i not in (4,5)] # only uppercase text on SA - ignore blank lines and labels on front (not top) of key
        if len(labels) < 1:
            return key_img # if blank, exit immediately

        scale_factor = 7
        min_size = 16
        line_spacing = 16
        if self.decal:
            offset = 0
            alignment = 'left'
        else:
            offset = 12 # pixels to shift text upwards to center it in keycap top
            alignment = 'center'
        width_limit = key_img.width - 42 # 60 is combined width of keycap sides in base image

        gotham = ImageFont.truetype(self.font_path, int(self.font_size*scale_factor)+min_size)
        draw = ImageDraw.Draw(key_img)
        w = max([gotham.getsize(text)[0] for text in labels]) # max of label widths
        if w > width_limit and not self.decal:
            labels = [line for label in labels for line in textwrap.wrap(label, width=int(width_limit/(gotham.getsize("L")[0])))]
            w = max([gotham.getsize(text)[0] for text in labels])
        h = sum([gotham.getsize(text)[1] for text in labels]) # sum of heights
        h += line_spacing*(len([text for text in labels])-1)
        c = ImageColor.getrgb(self.font_color)
        c = tuple(band + 0x26 for band in c) # Simulates reflectivity
        draw.multiline_text((int((key_img.width-w)/2), int((key_img.height-h)/2 - offset)), '\n'.join(labels), font=gotham, fill=c, spacing=line_spacing, align=alignment)
        return key_img 

    def render(self):
        if self.decal:
            key_img = self.decal_key()
        else:
            key_img = self.stretch_key()
            key_img = self.tint_key(key_img)
        key_img = self.text_key(key_img)
        key_img = key_img.rotate(-self.rotation_angle, resample=Image.BICUBIC, expand=1)
        return key_img
