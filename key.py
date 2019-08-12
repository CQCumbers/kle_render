import functools, math, requests
from PIL import Image, ImageMath, ImageColor, ImageCms, ImageDraw, ImageFont
from colormath import color_objects, color_conversions


class Key:
    __slots__ = [
        'x', 'y', 'width', 'height', 'x2', 'y2', 'width2', 'height2',
        'rotation_angle', 'rotation_x', 'rotation_y', 'custom_font',
        'res', 'flat', 'str_profile', 'decal', 'step', 'ghost', 'pic', 'color',
        'align', 'labels', 'label_sizes', 'label_colors', 'model_res',
    ]


    def __init__(self):
        self.x = self.y = 0.0
        self.width = self.height = 1.0
        self.x2 = self.y2 = 0.0
        self.width2 = self.height2 = 0.0

        self.rotation_angle = 0.0
        self.rotation_x = self.rotation_y = 0.0

        self.res = 200
        self.str_profile = 'SA'
        self.custom_font = self.flat = False
        self.decal = self.step = False
        self.ghost = self.pic = False
        self.color = '#EEEEEE'

        self.align = None
        self.labels = []
        self.label_sizes = [3.0] * 12
        self.label_colors = ['#000000'] * 12
        self.model_res = 0.01905


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
        if self.custom_font: return 'font.ttf'
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

    
    def get_label_props(self):
        if self.decal:
            props = {'margin_x': .48, 'margin_top': .2, 'margin_bottom': .2, 'line_spacing': .08}
        elif self.get_full_profile()[0] == 'GMK':
            props = {'margin_x': .22, 'margin_top': .14, 'margin_bottom': .34, 'line_spacing': .06}
        else:
            props = {'margin_x': .22, 'margin_top': .16, 'margin_bottom': .29, 'line_spacing': .08}
        props = {k: int(v * self.res) for k, v in props.items()}

        # center SA and decal labels if not explicitly aligned
        align = self.align if self.align else 0
        if self.align == None and (self.decal or self.get_full_profile()[0] != 'GMK'):
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
            rx, ry, a = self.rotation_x, self.rotation_y, math.radians(self.rotation_angle)
            x2, y2 = x * math.cos(a) - y * math.sin(a), y * math.cos(a) + x * math.sin(a)

            left, top = -self.width / 2, -self.height / 2
            left2, top2 = left * math.cos(a) - top * math.sin(a), top * math.cos(a) + left * math.sin(a)

            x, y = rx + x2 - key_img.width / u / 2 - left2, ry + y2 - key_img.height / u / 2 - top2
        return (int(i) for i in (x * u, y * u, x * u + key_img.width, y * u + key_img.height))


    def get_model_location(self):
        # get bounding box of model in x/y plane
        x, y, res = min(self.x, self.x + self.x2), min(self.y, self.y + self.y2), self.model_res
        width = max(self.width2 + abs(self.x2), self.width)
        height = max(self.height2 + abs(self.y2), self.height)
        if self.rotation_angle != 0 or self.rotation_x != 0 or self.rotation_y != 0:
            rx, ry, a = self.rotation_x, self.rotation_y, math.radians(self.rotation_angle)
            x, y = rx + x * math.cos(a) - y * math.sin(a), ry + y * math.cos(a) + x * math.sin(a)
            width, height = width * math.cos(a) - height * math.sin(a), height * math.cos(a) + width * math.sin(a)
        return (x, y, x + width, y + height)


    def get_base_img(self, full_profile):
        if self.flat:
            res, color, row, sizes = self.res, self.color, full_profile[1], {'ISO': (1.5, 2), 'BIGENTER': (2.25, 2)}
            return Image.new('RGBA', [int(res * x) for x in sizes.get(row, (1, 1))], color=ImageColor.getrgb(color))
        return open_base_img(full_profile, self.res, self.get_base_color(), self.color)


    def get_base_model(self, full_profile, scene):
        return copy_model('{0}_{1}'.format(*full_profile), scene)


    def get_decal_img(self):
        # calculate width and height of image to fit decal label
        label_props = self.get_label_props()
        font = ImageFont.truetype(self.get_font_path(), label_props['font_sizes'][0])
        w, h = text_size(self.labels[0], font, label_props['line_spacing'])
        key_img = Image.new('RGBA', (w + label_props['margin_x'] * 2, h + label_props['margin_top'] * 2))
        return key_img


    def get_decal_model(self, scene):
        # copy dimensions of image decal
        width, height = self.get_decal_img().size
        model = copy_model('DECAL', scene)
        self.stretch_model(model, width / self.res, height / self.res)
        return model


    def stretch_img(self, base_img, width, height): 
        w, h = base_img.size
        new_img = Image.new('RGBA', (width, height)) 
        new_img.paste(base_img, (0, 0, base_img.width, base_img.height))

        # stretch or crop base image horizontally
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


    def stretch_model(self, model, width, height):
        if width > 1:
            # shift right section right
            for v in model.data.vertices:
                v.co[0] -= (width - 1) * self.model_res if v.co[0] < -self.model_res / 2 else 0
        elif width < 1:
            # keep left section, compress middle section, shift right section left
            res, mid = self.model_res, width * self.model_res / 2
            for v in model.data.vertices:
                v.co[0] = v.co[0] if v.co[0] > -mid else (-mid if v.co[0] > -res + mid else v.co[0] + res - mid * 2)
            for p in model.data.polygons: p.use_smooth = False

        if height > 1:
            # shift bottom section down
            for v in model.data.vertices:
                v.co[1] += (height - 1) * self.model_res if v.co[1] > self.model_res / 2 else 0
        elif height < 1:
            # keep top section, compress middle section, shift bottom section up
            res, mid = self.model_res, height * self.model_res / 2
            for v in model.data.vertices:
                v.co[1] = v.co[1] if v.co[1] < mid else (mid if v.co[1] < res - mid else v.co[1] - res + mid * 2)
            for p in model.data.polygons: p.use_smooth = False

    
    def create_key(self):
        profile, row_profile = self.get_full_profile()
        if self.decal:
            return self.get_decal_img()
        elif row_profile in ('ISO', 'BIGENTER'):
            return self.get_base_img((profile, row_profile)).copy()
        elif self.width2 == 0.0 and self.height2 == 0.0:
            base_img = self.get_base_img((profile, row_profile))
            return self.stretch_img(base_img, int(self.width * self.res + 1), int(self.height * self.res))
        else:
            # calculate total width of keycap
            u, x2, y2 = self.res, self.x2, self.y2
            width = max(self.width2 + x2, self.width) if x2 >= 0 else max(self.width - x2, self.width2)
            height = max(self.height2 + y2, self.height) if y2 >= 0 else max(self.height - y2, self.height2)
            # create touch surface
            key_img = Image.new('RGBA', (int(width * u + 1), int(height * u)))
            base_img = self.get_base_img((profile, 'BASE'))
            touch_surface = self.stretch_img(base_img, int(self.width * u + 1), int(self.height * u))
            key_img.paste(touch_surface, (max(int(-x2 * u), 0), max(int(-y2 * u), 0)))

            if row_profile == 'STEP':
                overlap = int(0.3 * self.res)
                # add left step
                if x2 < 0:
                    left_img = self.get_base_img((profile, row_profile)).copy().transpose(Image.FLIP_LEFT_RIGHT)
                    left_step = self.stretch_img(left_img, int(-x2 * u + overlap + 1), int(height * u))
                    key_img.paste(left_step, (0, 0))
                # add right step
                if max(-x2, 0) + self.width < width: 
                    right_img = self.get_base_img((profile, row_profile))
                    img_width = int((width - self.width - max(-x2, 0)) * u + overlap + 1)
                    right_step = self.stretch_img(right_img, img_width, int(height * u))
                    img_x = int((max(-x2, 0) + self.width) * u - overlap)
                    key_img.paste(right_step, (img_x, 0))
            else:
                # handle arbitrary second surface
                extra_img = self.get_base_img((profile, row_profile))
                extra_surface = self.stretch_img(extra_img, int(self.width2 * u + 1), int(self.height2 * u))
                key_img.paste(extra_surface, (max(int(x2 * u), 0), max(int(y2 * u), 0)))

            return key_img


    def create_model(self, scene):
        profile, row_profile = self.get_full_profile()
        if self.str_profile.startswith('DSA'): profile = 'DSA'

        if self.decal:
            return self.get_decal_model(scene)
        elif row_profile in ('ISO', 'BIGENTER'):
            return self.get_base_model((profile, row_profile), scene)
        elif self.width2 == 0.0 and self.height2 == 0.0:
            model = self.get_base_model((profile, row_profile), scene)
            self.stretch_model(model, self.width, self.height)
            return model
        else:
            # calculate total width of keycap
            model_res, x2, y2 = self.model_res, self.x2, self.y2
            width = max(self.width2 + x2, self.width) if x2 >= 0 else max(self.width - x2, self.width2)
            height = max(self.height2 + y2, self.height) if y2 >= 0 else max(self.height - y2, self.height2)
            # create touch surface
            key_model = self.get_base_model((profile, 'BASE'), scene)
            self.stretch_model(key_model, self.width, self.height)
            # move touch surface mesh relative to object origin
            for v in key_model.data.vertices:
                v.co[0] -= max(-x2, 0) * model_res
                v.co[1] += max(-y2, 0) * model_res
            
            if row_profile == 'STEP':
                # add left step
                if x2 < 0:
                    left_step = self.get_base_model((profile, row_profile), scene)
                    for v in left_step.data.vertices: v.co[0] = -model_res * 0.97 - v.co[0]
                    self.stretch_model(left_step, -x2 + 0.333, height)
                    left_step.parent = key_model
                # add right step
                if max(-x2, 0) + self.width < width: 
                    right_step = self.get_base_model((profile, row_profile), scene)
                    self.stretch_model(right_step, width - self.width - max(-x2, 0) + 0.333, height)
                    right_step.location = (-(max(-x2, 0) + self.width - 0.333) * model_res, 0, 0)
                    right_step.parent = key_model
            else:
                # handle arbitrary second surface
                extra_model = self.get_base_model((profile, row_profile), scene)
                self.stretch_model(extra_model, self.width2, self.height2)
                extra_model.location = (-max(x2 * model_res, 0), max(y2 * model_res, 0), 0)
                extra_model.parent = key_model

            return key_model


    def pic_key(self, key_img):
        try:
            props = self.get_label_props()
            width, height = int(self.width * self.res), int(self.height * self.res)
            size = (width - props['margin_x'] * 2, height - props['margin_top'] - props['margin_bottom'])
            with Image.open(requests.get(self.labels[0], stream=True).raw) as label_img:
                label_img.thumbnail(size)
                label_back = Image.new('RGBA', size)
                position = int((size[0] - label_img.size[0]) / 2), int((size[1] - label_img.size[1]) / 2)
                label_back.paste(label_img, position, mask=label_img)
                key_img.paste(label_back, (props['margin_x'], props['margin_top']), mask=label_back)
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
            text = break_text(text, font, width - props['margin_x'] * 2) if not self.decal else text
            text = text.upper() if self.get_full_profile()[0] == 'SA' and not self.decal else text
            text_width, text_height = text_size(text, font, props['line_spacing'])
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
        key_img = self.label_key(self.create_key())
        if self.ghost: key_img.putalpha(Image.new('L', key_img.size, color=64))
        if not flat: key_img = key_img.rotate(-self.rotation_angle, resample=Image.BILINEAR, expand=1)
        return key_img

    
    def model(self, scene):
        # create model, then rotate and place
        model = self.create_model(scene)
        location, res = self.get_model_location(), self.model_res
        model.rotation_euler = (0, 0, math.radians(-self.rotation_angle))
        model.location = (-location[0] * res, location[1] * res, 0)
        return model


srgb_profile, lab_profile = ImageCms.createProfile('sRGB'), ImageCms.createProfile('LAB', colorTemp=5000)
rgb2lab_transform = ImageCms.buildTransformFromOpenProfiles(srgb_profile, lab_profile, 'RGB', 'LAB')
lab2rgb_transform = ImageCms.buildTransformFromOpenProfiles(lab_profile, srgb_profile, 'LAB', 'RGB')


@functools.lru_cache()
def open_base_img(full_profile, res, base_color, color):
    # get base image according to profile and perceptual gray of key color
    base_num = str([0xE0, 0xB0, 0x80, 0x50, 0x20].index(base_color) + 1)

    # open image and convert to Lab
    with Image.open('images/{0}_{1}{2}.png'.format(*full_profile, base_num)) as img:
        key_img = img.resize((int(s * res / 200) for s in img.size), resample=Image.BILINEAR).convert('RGBA')
    if full_profile[1] in ('ISO', 'BIGENTER'): alpha = key_img.split()[-1]
    l, a, b = ImageCms.applyTransform(key_img, rgb2lab_transform).split()

    # convert key color to Lab
    # a and b should be scaled by 128/100, but desaturation looks more natural
    rgb_color = color_objects.sRGBColor(*ImageColor.getrgb(color), is_upscaled=True)
    lab_color = color_conversions.convert_color(rgb_color, color_objects.LabColor)
    l1, a1, b1 = lab_color.get_value_tuple()
    l1, a1, b1 = int(l1 * 256 / 100), int(a1 + 128), int(b1 + 128)

    # change Lab of base image to match that of key color
    l = ImageMath.eval('convert(l + l1 - l_avg, "L")', l=l, l1=l1, l_avg=base_color)
    a = ImageMath.eval('convert(a + a1 - a, "L")', a=a, a1=a1)
    b = ImageMath.eval('convert(b + b1 - b, "L")', b=b, b1=b1)

    key_img = ImageCms.applyTransform(Image.merge('LAB', (l, a, b)), lab2rgb_transform).convert('RGBA')
    if full_profile[1] in ('ISO', 'BIGENTER'): key_img.putalpha(alpha)
    return key_img


@functools.lru_cache()
def break_text(text, font, limit):
    if not ' ' in text: return text
    words, lines = text.split(' '), ['']
    while words:
        word = words.pop(0)
        if font.getsize(lines[-1] + word)[0] + 1 < limit or len(lines[-1]) < 1:
            lines[-1] += word + ' '
        else:
            lines.append(word + ' ')
    return '\n'.join([line[:-1] for line in lines])


@functools.lru_cache()
def text_size(text, font, line_spacing):
    lines = text.splitlines()
    if len(lines) < 1: return (0, 0)

    widths, heights = zip(*(font.getsize(line) for line in lines if len(line) > 0))
    # max of line widths, sum of line heights
    w, h = max(widths), sum(heights)
    h += line_spacing * (len(lines) - 1)
    return (w, h)


def copy_model(name, scene):
    # duplicate object properties and data, link to scene
    original_model = scene.objects.get(name)
    model = original_model.copy()
    model.data = original_model.data.copy()
    scene.collection.objects.link(model)
    return model
