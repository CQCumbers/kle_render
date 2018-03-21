import functools, math, requests, io
from PIL import Image, ImageMath, ImageColor, ImageCms, ImageDraw, ImageFont, ImageFilter
from colormath.color_objects import LabColor, sRGBColor
from colormath.color_conversions import convert_color

srgb_profile = ImageCms.createProfile('sRGB')
lab_profile = ImageCms.createProfile('LAB')
rgb2lab_transform = ImageCms.buildTransformFromOpenProfiles(srgb_profile, lab_profile, 'RGB', 'LAB')
lab2rgb_transform = ImageCms.buildTransformFromOpenProfiles(lab_profile, srgb_profile, 'LAB', 'RGB')


class Key:
    __slots__ = [
        'x', 'y', 'width', 'height', 'x2', 'y2', 'width2', 'height2',
        'rotation_angle', 'rotation_x', 'rotation_y',
        'res', 'flat', 'str_profile', 'decal', 'step', 'pic', 'color',
        'align', 'labels', 'label_sizes', 'label_colors',
    ]


    def __init__(self):
        self.x = self.y = 0.0
        self.width = self.height = 1.0
        self.x2 = self.y2 = 0.0
        self.width2 = self.height2 = 0.0

        self.rotation_angle = 0.0
        self.rotation_x = self.rotation_y = 0.0

        self.res = 200
        self.flat = False
        self.str_profile = 'SA'
        self.decal = self.step = self.pic = False
        self.color = '#EEEEEE'

        self.align = None
        self.labels = []
        self.label_sizes = [3.0] * 12
        self.label_colors = ['#000000'] * 12


    @functools.lru_cache()
    def get_full_profile(self):
        # only GMK and SA base images
        full_profile = self.str_profile.upper().split(' ')
        profile = 'GMK' if full_profile[0] in ('GMK', 'DCS', 'OEM') else 'SA'

        # row profile used to specify keys with special base images
        props = (self.width, self.height, self.x2, self.y2, self.width2, self.height2)
        special_keys = {
            (1.5, 1.0, 0.25, 0.0, 1.25, 2.0): 'ISO',
            (1.25, 2.0, -0.25, 0.0, 1.5, 1.0): 'ISO',
            (1.5, 2.0, -0.75, 1.0, 2.25, 1.0): 'BIGENTER'
        } 
        if props in special_keys:
            row_profile = special_keys[props]
        elif self.step and self.height == self.height2:
            row_profile = 'STEP'
        elif (self.width >= 6.0 and self.height == 1.0) or (full_profile[-1] == 'SPACE'):
            row_profile = 'SPACE'
        else:
            row_profile = 'BASE'

        return (profile, row_profile)


    @functools.lru_cache()
    def get_font_path(self):
        return 'fonts/{}_font.ttf'.format(self.get_full_profile()[0])


    @functools.lru_cache()
    def get_base_color(self):
        # calculate perceptual gray of key color
        color = ImageColor.getrgb(self.color)
        bright = 0.3 * color[0] + 0.59 * color[1] + 0.11 * color[2] 

        # get corresponding base image's average color
        if (bright > 0xB0):
            return 0xE0  # 224
        elif (bright > 0x80):
            return 0xB0  # 176
        elif (bright > 0x50):
            return 0x80  # 128
        elif (bright > 0x20):
            return 0x50  # 80
        else:
            return 0x20  # 32

    
    @functools.lru_cache()
    def get_label_props(self):
        if self.decal:
            props = {'margin_x': .48, 'margin_top': .2, 'margin_bottom': .2, 'line_spacing': .08}
        elif self.get_full_profile()[0] == 'GMK':
            props = {'margin_x': .22, 'margin_top': .14, 'margin_bottom': .32, 'line_spacing': .06}
        else:
            props = {'margin_x': .22, 'margin_top': .16, 'margin_bottom': .29, 'line_spacing': .08}
        props = {k: int(v * self.res) for k, v in props.items()}

        # center SA and decal labels if not explicitly aligned
        align = self.align if self.align else 0
        if self.align == None and (self.get_full_profile()[0] == 'SA' or self.decal):
            align = 7 if len(self.labels) == 1 else 5 if len(self.labels) <= 3 else 0

        # calculate row/column and font size of each label
        pattern = [0, 8, 2, 6, 9, 7, 1, 10, 3, 4, 11, 5]
        center_front, center_row, center_col = [digit == '1' for digit in '{0:03b}'.format(align)]
        props.update({'font_sizes': [], 'positions': []})
        for i in range(min(len(self.labels), 12)):
            row, col = (int(pattern.index(i) / 3), pattern.index(i) % 3)
            col = (1 if col < 1 else None) if (center_col and row < 3) or (center_front and row > 2) else col
            row = (1 if row < 1 else None) if (center_row and row < 3) else row
            label_size = self.label_sizes[i] if row != None and row < 3 else 3.0
            props['font_sizes'].append(int(.09 * self.res + .03 * self.res * label_size))
            props['positions'].append((row, col))

        return props


    def get_location(self, key_img): 
        # get pixel location of key as (left, upper, right, lower)
        u = self.res
        x, y = min(self.x, self.x + self.x2), min(self.y, self.y + self.y2)

        if self.rotation_angle != 0 or self.rotation_x != 0 or self.rotation_y != 0:
            # center about which to rotate key
            rx, ry = self.rotation_x, self.rotation_y 
            a = self.rotation_angle * math.pi / 180
            x2, y2 = x * math.cos(a) - y * math.sin(a), y * math.cos(a) + x * math.sin(a)

            left, top = -self.width / 2, -self.height / 2
            left2, top2 = left * math.cos(a) - top * math.sin(a), top * math.cos(a) + left * math.sin(a)

            x, y = rx + x2 - key_img.width / u / 2 - left2, ry + y2 - key_img.height / u / 2 - top2
        return (int(i) for i in (x * u, y * u, x * u + key_img.width, y * u + key_img.height))


    def get_base_img(self, full_profile):
        # get base image according to profile and perceptual gray of key color
        base_num = str([0xE0, 0xB0, 0x80, 0x50, 0x20].index(self.get_base_color()) + 1)
        if self.flat: return Image.new('RGBA', (self.res,) * 2, color=(self.get_base_color(),) * 3)
        img = Image.open('images/{}_{}{}.png'.format(*full_profile, base_num)).convert('RGBA')
        return img.resize((int(s * self.res / 200) for s in img.size), resample=Image.BILINEAR)


    def get_decal_img(self):
        # calculate width and height of image to fit decal label
        label_props = self.get_label_props()
        font = ImageFont.truetype(self.get_font_path(), label_props['font_sizes'][0])
        w, h = self.text_size(self.labels[0], font, label_props['line_spacing'])
        key_img = Image.new('RGBA', (w + label_props['margin_x'] * 2, h + label_props['margin_top'] * 2))
        return key_img


    def stretch_img(self, base_img, width, height): 
        w, h = base_img.size
        new_img = Image.new('RGBA', (width, height)) 
        new_img.paste(base_img, (0, 0, base_img.width, base_img.height))

        # stretch or crop base image horizontally
        # gaussian blur to reduce stretch lines
        if width > w:
            center_part = base_img.crop((int(w / 2), 0, int(w / 2) + 10, h))
            right_part = base_img.crop((int(w / 2) + 1, 0, w, h))
            for i in range(1, width - w + 1, 10):
                new_img.paste(center_part, (int(w / 2) + i, 0, int(w / 2) + i + 10, h))
            new_img.paste(right_part, (width - right_part.width, 0, width, h))
        elif width < w:
            right_part = base_img.crop((w - int(width / 2), 0, w, h))
            new_img.paste(right_part, (width - right_part.width, 0, width, h))

        # stretch or crop base image vertically
        if height > h:
            middle_part = new_img.crop((0, int(h / 2), width, int(h / 2) + 10))
            bottom_part = new_img.crop((0, int(h / 2) + 1, width, h))
            for i in range(1, height - h + 1, 10):
                new_img.paste(middle_part, (0, int(h / 2) + i, new_img.width, int(h / 2) + i + 10))
            new_img.paste(bottom_part, (0, height - bottom_part.height, width, height))
        elif height < h:
            bottom_part = new_img.crop((0, h - int(height / 2), width, h))
            new_img.paste(bottom_part, (0, height - bottom_part.height, width, height))

        return new_img

    
    def create_key(self):
        profile, row_profile = self.get_full_profile()
        if self.decal:
            return self.get_decal_img()
        elif row_profile in ('ISO', 'BIGENTER'):
            return self.get_base_img((profile, row_profile))
        elif self.width2 == 0.0 and self.height2 == 0.0:
            base_img = self.get_base_img((profile, row_profile))
            return self.stretch_img(base_img, int(self.width * self.res + 1), int(self.height * self.res))
        else:
            # calculate total width of keycap
            u, x2, y2 = self.res, self.x2, self.y2
            width = max(self.width2 + self.x2, self.width) if x2 >= 0 else max(self.width - x2, self.width2)
            height = max(self.height2 + self.y2, self.height) if y2 >= 0 else max(self.height - y2, self.height2)
            # create touch surface
            key_img = Image.new('RGBA', (int(width * u + 1), int(height * u)))
            base_img = self.get_base_img((profile, 'BASE'))
            touch_surface = self.stretch_img(base_img, int(self.width * u + 1), int(self.height * u))
            key_img.paste(touch_surface, (max(int(-x2 * u), 0), max(int(-y2 * u), 0)))

            if row_profile == 'STEP':
                overlap = int(0.3 * self.res)
                # add left step
                if x2 < 0:
                    left_img = self.get_base_img((profile, row_profile)).transpose(Image.FLIP_LEFT_RIGHT)
                    left_step = self.stretch_img(left_img, int(-x2 * u + overlap + 1), int(height * u))
                    key_img.paste(left_step, (max(int(x2 * u), 0), max(int(y2 * u), 0)))
                # add right step
                if max(x2 * u, 0) + self.width < width: 
                    right_img = self.get_base_img((profile, row_profile))
                    img_width = int((width - max(-x2, 0) - self.width) * u + overlap + 1)
                    right_step = self.stretch_img(right_img, img_width, int(height * u))
                    key_img.paste(right_step, (max(int(-x2 * u), 0) + int(self.width * u) - overlap, 0))
            else:
                # handle arbitrary second surface
                extra_img = self.get_base_img((profile, row_profile))
                extra_surface = self.stretch_img(extra_img, int(self.width2 * u + 1), int(self.height2 * u))
                key_img.paste(extra_surface, (max(int(x2 * u), 0), max(int(y2 * u), 0)))

            return key_img


    def tint_key(self, key_img): 
        # get base image in Lab form
        alpha = key_img.split()[3]
        key_img = ImageCms.applyTransform(key_img, rgb2lab_transform)
        l, a, b = key_img.split()

        # convert key color to Lab
        # a1 and b1 should be scaled by 128/100, but desaturation looks more natural
        rgb_color = sRGBColor(*ImageColor.getrgb(self.color), is_upscaled=True)
        lab_color = convert_color(rgb_color, LabColor)
        l1, a1, b1 = lab_color.get_value_tuple()
        l1, a1, b1 = int(l1 * 256 / 100), int(a1 + 128), int(b1 + 128)

        # change Lab of base image to match that of key color
        l = ImageMath.eval('l + l1 - l_avg', l=l, l1=l1, l_avg=self.get_base_color()).convert('L')
        a = ImageMath.eval('a + a1 - a', a=a, a1=a1).convert('L')
        b = ImageMath.eval('b + b1 - b', b=b, b1=b1).convert('L')

        key_img = Image.merge('LAB', (l, a, b))
        key_img = ImageCms.applyTransform(key_img, lab2rgb_transform)
        key_img = Image.merge('RGBA', (*key_img.split(), alpha))
        return key_img


    def break_text(self, text, font, limit):
        words, lines = text.split(' '), ['']
        while words:
            word = words.pop(0)
            if font.getsize(lines[-1] + word)[0] + 1 < limit or len(lines[-1]) < 1:
                lines[-1] += word + ' '
            else:
                lines.append(word + ' ')
        return '\n'.join([line[:-1] for line in lines])


    def text_size(self, text, font, line_spacing):
        lines = text.splitlines()
        if len(lines) < 1: return (0, 0)

        w = max([font.getsize(line)[0] for line in lines])  # max of line widths
        h = sum([font.getsize(line)[1] for line in lines])  # sum of line heights
        h += line_spacing * (len(lines) - 1)
        return (w, h)


    def pic_key(self, key_img):
        try:
            props = self.get_label_props()
            position = (x_offset + props['margin_x'], y_offset + props['margin_top'])
            size = (width - props['margin_x'] * 2, height - props['margin_top'] - props['margin_bottom'])
            label_img = Image.open(requests.get(self.labels[0], stream=True).raw).resize(size)
            key_img.paste(label_img, position, mask=label_img)
            return key_img
        except Exception:
            return key_img


    def label_key(self, key_img):
        # if blank, exit immediately
        if len(self.labels) < 1: return key_img
        if self.pic: return self.pic_key(key_img)

        props = self.get_label_props()
        width, height = int(self.width * self.res), int(self.height * self.res)
        x_offset, y_offset = max(int(-self.x2 * self.res), 0), max(int(-self.y2 * self.res), 0)
        col2x = [
            lambda w: props['margin_x'] + x_offset,
            lambda w: (width - w) / 2 + x_offset,
            lambda w: width - props['margin_x'] - w + x_offset
        ]
        row2y = [
            lambda h: props['margin_top'] + y_offset,
            lambda h: (height - props['margin_bottom'] + props['margin_top'] - h) / 2 + y_offset,
            lambda h: height - props['margin_bottom'] - h + y_offset,
            lambda h: props['margin_top'],
        ]
        aligns = ['left', 'center', 'right']
        # seperate surface for front printed labels
        top_draw = ImageDraw.Draw(key_img)
        front_plane = Image.new('RGBA', (width, max(height - props['margin_bottom'] * 2, 1)))
        front_draw = ImageDraw.Draw(front_plane)

        for i in range(min(len(self.labels), 12)):
            (row, col), text = props['positions'][i], self.labels[i]
            if not text or row == None: continue

            # load font and calculate text dimensions
            font = ImageFont.truetype(self.get_font_path(), props['font_sizes'][i])
            text = self.break_text(text, font, width - props['margin_x'] * 2) if not self.decal else text
            text = text.upper() if self.get_full_profile()[0] == 'SA' and not self.decal else text
            text_width, text_height = self.text_size(text, font, props['line_spacing'])
            # retrieve label color and lighten to simulate reflectivity
            color = ImageColor.getrgb(self.label_colors[i])
            color = color if self.flat else tuple(band + 0x26 for band in color)

            # draw labels accordings to row/col of props
            (front_draw if row == 3 else top_draw).multiline_text(
                (col2x[col](text_width), row2y[row](text_height)), text, font=font,
                fill=color, spacing=props['line_spacing'], align=aligns[col]
            )

        # compress front printed labels vertically
        front_plane = front_plane.resize((width, props['margin_bottom']), resample=Image.BILINEAR)
        key_img.paste(front_plane, (x_offset, height - props['margin_bottom'] + y_offset), mask=front_plane)
        return key_img


    def render(self, scale, flat):
        self.res, self.flat = int(self.res / scale), flat
        # create key, then tint key, then label key
        key_img = self.label_key(self.tint_key(self.create_key()))
        return key_img.rotate(-self.rotation_angle, resample=Image.BILINEAR, expand=1)
