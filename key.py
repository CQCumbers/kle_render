from PIL import Image, ImageMath, ImageColor, ImageCms, ImageDraw, ImageFont, ImageFilter
from colormath.color_objects import LabColor, sRGBColor
from colormath.color_conversions import convert_color
import math

srgb_profile = ImageCms.createProfile('sRGB')
lab_profile = ImageCms.createProfile('LAB')
rgb2lab_transform = ImageCms.buildTransformFromOpenProfiles(srgb_profile, lab_profile, 'RGB', 'LAB')
lab2rgb_transform = ImageCms.buildTransformFromOpenProfiles(lab_profile, srgb_profile, 'LAB', 'RGB')

GMK_LABELS = ('GMK', 'DCS', 'OEM')

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
        self.width2 = 0.0
        self.height2 = 0.0
        self.color = '#EEEEEE'
        self.font_color = ['#000000']
        self.font_size = [3.0] * 12
        self.labels =[]
        self.align = -1
        self.rotation_angle = 0.0
        self.rotation_x = 0.0
        self.rotation_y = 0.0
        self.profile = ''
        self.nub = False
        self.ghost = False
        self.stepped = False
        self.decal = False

    def font_path(self):
        if self.profile.startswith(GMK_LABELS):
            return 'fonts/GMK_font.ttf'
        else:
            return 'fonts/SA_font.ttf'

    def get_base_img(self, full_profile=[]):
        full_profile = self.profile.split(' ') if len(full_profile) < 1 else full_profile
        row_profiles = ['SPACE', 'ISO', 'BIGENTER', 'STEP', 'BASE'] # row profile internally used to specify keys needing special base images
        profile = 'GMK' if full_profile[0] in GMK_LABELS else 'SA'
        row = full_profile[1] if len(full_profile) > 1 and full_profile[1] in row_profiles else 'BASE'

        if self.width >= 6.0 and self.height == 1.0: # Default make long, narrow keys spacebars
            row = 'SPACE'

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

        return Image.open('images/{}_{}{}.png'.format(profile, row, base_num)).convert('RGBA') # All renders by CQ_Cumbers (me)

    def get_base_color(self):
        color = ImageColor.getrgb(self.color)
        bright = 0.3*color[0] + 0.59*color[1] + 0.11*color[2] # Perceptual gray
        if (bright > 0xB0):
            return 0xE0 # 224
        elif (bright > 0x80):
            return 0xB0 # 176
        elif (bright > 0x50):
            return 0x80 # 128
        elif (bright > 0x20):
            return 0x50 # 80,
        else:
            return 0x20 # 32

    def location(self, key_img): # get pixel location of key as (left, upper, right, lower)
        u = self.u
        x, y = min(self.x, self.x+self.x2), min(self.y, self.y+self.y2)
        if self.rotation_angle != 0 or self.rotation_x != 0 or self.rotation_y != 0:
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

        l1, a1, b1 = lab_color.get_value_tuple()
        l1 = int(l1*256/100)
        a1 = int(a1+128) #a1 should be scaled by 128/100, but desaturation looks more natural
        b1 = int(b1+128)
        l = ImageMath.eval('l + l1 - l2', l=l, l2=self.base_color, l1=l1).convert('L')
        a = ImageMath.eval('a - a + a1', a=a, a1=a1).convert('L')
        b = ImageMath.eval('b - b + b1', b=b, b1=b1).convert('L')

        key_img = Image.merge('LAB', (l, a, b))
        key_img = ImageCms.applyTransform(key_img, lab2rgb_transform)
        key_img = Image.merge('RGBA', (*key_img.split(), alpha))
        return key_img

    def stretch_key(self, w, h, img=None): # width and height of key in units
        if img is None:
            base_img = self.get_base_img()
        else:
            base_img = img
        u = self.u
        width, height = int(w*u)+1, int(h*u)+1 # Width & Height of image representing key
        key_img = Image.new('RGBA', (width, height)) # Lots of +1s to avoid unsightly gaps between keys
        key_img.paste(base_img, (0, 0, base_img.width, base_img.height))
        if width > u+1:
            center_part = base_img.crop((int(u/2), 0, int(u/2)+1, u)).filter(ImageFilter.GaussianBlur()) # horizontal middle strip of image, attempt to reduce stretch lines
            right_part = base_img.crop((int(u/2)+1, 0, u, u))
            for i in range(width - u + 1):
                key_img.paste(center_part, (int(u/2) + i, 0, int(u/2) + i + 1, u))
            key_img.paste(right_part, (width - right_part.width, 0, width, u))
        elif width < u+1:
            right_part = base_img.crop((u-int(width/2), 0, u, u))
            key_img.paste(right_part, (width - right_part.width, 0, width, u))
        if height > u+1:
            middle_part = key_img.crop((0, int(u/2), width, int(u/2)+1)).filter(ImageFilter.GaussianBlur()) # vertical middle strip of image, attempt to reduce stretch lines
            bottom_part = key_img.crop((0, int(u/2)+1, width, u))
            for i in range(height - u + 1):
                key_img.paste(middle_part, (0, int(u/2) + i, key_img.width, int(u/2) + i + 1))
            key_img.paste(bottom_part, (0, height - bottom_part.height, width, height))
        elif height < u+1:
            bottom_part = key_img.crop((0, u-int(height/2), width, u))
            key_img.paste(bottom_part, (0, height - bottom_part.height, width, height))
        return key_img

    def decal_key(self):
        scale_factor = 8
        min_size = 8
        line_spacing = 16
        labels = [text.upper() for text in self.labels] # only uppercase text on SA

        font = ImageFont.truetype(self.font_path(), int(max(self.font_size)*scale_factor)+min_size)
        w = max([font.getsize(text)[0] for text in labels]) # max of widths
        h = sum([font.getsize(text)[1] for text in labels]) # sum of heights
        h += line_spacing*(len([text for text in labels if len(text) > 0]))

        key_img = Image.new('RGBA', (w+64, h+108))
        return key_img

    def break_text(self, input, font, limit):
        texts = input.splitlines()
        output = []
        for text in texts:
            words = text.split()
            lines = [[]]
            while(words):
                word = words.pop(0)
                if font.getsize(" ".join(lines[-1]))[0] + 1 + font.getsize(word)[0] < limit:
                    lines[-1].append(word)
                else:
                    lines.append([word])
            output.extend([' '.join(words) for words in lines if len(words) > 0])
        return '\n'.join(output)

    def text_size(self, full_label, font, line_spacing): #full label should already have break_text used on it
        labels = full_label.splitlines()
        w = max([font.getsize(text)[0] for text in labels])
        h = sum([font.getsize(text)[1] for text in labels]) # sum of heights
        h += line_spacing*(len([text for text in labels])-1)
        return (w, h)

    def text_key(self, key_img):
        labels = self.labels
        if len(labels) <= 0:
            return key_img # if blank, exit immediately
        else:
            margin = 45
            if self.decal:
                offset = 0 # pixels to shift text upwards to center it in keycap top
                scale_factor = 6 # multiply this by the legend size and add to min_size to get font size for that legend
                min_size = 18
                line_spacing = 16 # space between lines (only matters for <= 2 labels)
                width_limit = key_img.width # maximum line width in pixels before automatic line break (Only matters for 1 label)
            elif self.profile.startswith(GMK_LABELS):
                offset = 12
                scale_factor = 6
                min_size = 18
                line_spacing = 12
                width_limit = key_img.width - 78
            else:
                offset = 12
                scale_factor = 6
                min_size = 18
                line_spacing = 16
                width_limit = key_img.width - 64
                labels = [labels[i].upper() for i in range(len(labels))] # Only uppercase legends on SA keycaps

            draw = ImageDraw.Draw(key_img)

            if self.align == -1: # if not explicitly aligned
                if not self.profile.startswith(GMK_LABELS) and not self.decal and labels[0] != '': # If single label and not explicitly aligned, default center align SA profile
                    if len(labels) == 1:
                        self.align = 7
                    elif len(labels) <= 3:
                        self.align = 5
                    else:
                        self.align = 0
                else:
                    self.align = 0
            
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
                if labels[i].strip(): # ignores empty and whitespace only strings
                    font = ImageFont.truetype(self.font_path(), int((self.font_size[i] if i not in align[9:] else 3.0)*scale_factor)+min_size)
                    text = self.break_text(labels[i], font, width_limit)
                    w, h = self.text_size(text, font, line_spacing)
                    c = ImageColor.getrgb(self.font_color[i] if i < len(self.font_color) and len(self.font_color[i]) > 0 else self.font_color[0]) # color defaults to first if unspecified
                    c = tuple(band + 0x26 for band in c) # Simulates reflectivity 
                    if i == align[0]:
                        draw.multiline_text((margin, margin-offset), text, font=font, fill=c, spacing=line_spacing, align='left')
                    elif i == align[6]:
                       draw.multiline_text((margin, key_img.height-margin-h-offset), text, font=font, fill=c, spacing=line_spacing, align='center')
                    elif i == align[2]:
                        draw.multiline_text((key_img.width-margin-w, margin-offset), text, font=font, fill=c, spacing=line_spacing, align='right')
                    elif i == align[8]:
                        draw.multiline_text((key_img.width-margin-w, key_img.height-margin-h-offset), text, font=font, fill=c, spacing=line_spacing, align='left')
                    elif i == align[3]:
                        draw.multiline_text((margin, (key_img.height-h)/2-offset), text, font=font, fill=c, spacing=line_spacing, align='center')
                    elif i == align[5]:
                        draw.multiline_text((key_img.width-margin-w, (key_img.height-h)/2-offset), text, font=font, fill=c, spacing=line_spacing, align='right')
                    elif i == align[1]:
                        draw.multiline_text(((key_img.width-w)/2, margin-offset), text, font=font, fill=c, spacing=line_spacing, align='left')
                    elif i == align[4]:
                        draw.multiline_text(((key_img.width-w)/2, (key_img.height-h)/2-offset), text, font=font, fill=c, spacing=line_spacing, align='center')
                    elif i == align[7]:
                        draw.multiline_text(((key_img.width-w)/2, key_img.height-margin-h-offset), text, font=font, fill=c, spacing=line_spacing, align='right')
                    elif i in align[9:]:
                        front_plane = Image.new('RGBA', (key_img.width, 40*2))
                        draw2 = ImageDraw.Draw(front_plane)
                        if i == align[9]:
                            draw2.multiline_text((45, 0), text, font=font, fill=c, spacing=line_spacing, align='left')
                        elif i == align[10]:
                            draw2.multiline_text(((key_img.width-w)/2, 0), text, font=font, fill=c, spacing=line_spacing, align='center')
                        else:
                            draw2.multiline_text((key_img.width-45-w, 0), text, font=font, fill=c, spacing=line_spacing, align='right')
                        front_plane = front_plane.resize((key_img.width, 40))
                        key_img.paste(front_plane, (0, key_img.height-front_plane.height), mask=front_plane)
            return key_img

    def extend(self):
        x2, y2 = self.x2, self.y2
        u = self.u
        width = max(self.width2 + x2, self.width) if x2 >= 0 else max(self.width - x2, self.width2)
        height = max(self.height2 + y2, self.height) if y2 >= 0 else max(self.height - y2, self.height2)
        key_img = Image.new('RGBA', (int(width*u), int(height*u)))

        special_cases = {(1.5, 1.0, 0.25, 0.0, 1.25, 2.0):'ISO', (1.25, 2.0, -0.25, 0.0, 1.5, 1.0):'ISO', (1.5, 2.0, -0.75, 1.0, 2.25, 1.0):'BIGENTER'} # special case oddly shaped keys
        identifiers = (self.width, self.height, x2, y2, self.width2, self.height2)
        if identifiers in special_cases: # handle special cases with second rectangle (only for SA)
            key_img = self.get_base_img(full_profile=[self.profile.split(' ')[0], special_cases[identifiers]])
            key_img = self.tint_key(key_img)
            text = self.text_key(Image.new('RGBA', (int(self.width*u), int(self.height*u))))
            key_img.paste(text, (max(int(-x2*u), 0), max(int(-y2*u), 0)), mask=text)
        else:
            touch_surface = self.stretch_key(self.width, self.height)
            touch_surface = self.tint_key(touch_surface)
            if self.stepped == True and height == self.height == self.height2: # handle most stepped keys (only for SA)
                key_img.paste(touch_surface, (max(int(-x2*u), 0), max(int(-y2*u), 0)))
                overlap = 60 # how many pixels of overlap
                if x2 < 0: # for keys with left step
                    left_img = self.get_base_img(full_profile=[self.profile.split(' ')[0], 'STEP']).transpose(Image.FLIP_LEFT_RIGHT)
                    left_step = self.stretch_key(-x2+overlap/u, height, img=left_img)
                    left_step = self.tint_key(left_step)
                    key_img.paste(left_step, (max(int(x2*u), 0), max(int(y2*u), 0)))
                if max(x2*u, 0)+self.width < width: # for right and double stepped keys
                    right_img = self.get_base_img(full_profile=[self.profile.split(' ')[0], 'STEP'])
                    right_step = self.stretch_key(width-max(-x2, 0)-self.width+overlap/u, self.height, img=right_img)
                    right_step = self.tint_key(right_step)
                    key_img.paste(right_step, (max(int(-x2*u), 0)+int(self.width*u)-overlap, 0))
                text = self.text_key(Image.new('RGBA', (int(self.width*u), int(self.height*u))))
                key_img.paste(text, (max(int(-x2*u), 0), max(int(-y2*u), 0)), mask=text)
            else: # sorta handle arbitrary secondary rectangles
                touch_surface = self.text_key(touch_surface)
                extra_surface = self.stretch_key(self.width2, self.height2)
                extra_surface = self.tint_key(extra_surface)
                key_img.paste(extra_surface, (max(int(x2*u), 0), max(int(y2*u), 0)))
                key_img.paste(touch_surface, (max(int(-x2*u), 0), max(int(-y2*u), 0)))

        return key_img

    def render(self):
        self.base_color = self.get_base_color()

        if self.decal:
            key_img = self.decal_key()
            key_img = self.text_key(key_img)
        elif self.width2 != 0.0 or self.height2 != 0.0:
            key_img = self.extend()
        else:
            key_img = self.stretch_key(self.width, self.height)
            key_img = self.tint_key(key_img)
            key_img = self.text_key(key_img)

        key_img = key_img.resize(tuple(i+2 for i in key_img.size))
        key_img = key_img.rotate(-self.rotation_angle, resample=Image.BICUBIC, expand=1)
        return key_img
