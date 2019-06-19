import copy, html, lxml.html, re, json
from PIL import Image, ImageColor, ImageDraw, ImageFont
from key import Key


class Keyboard:
    __slots__ = ['keys', 'keyboard', 'max_size', 'color']


    def __init__(self, json):
        # parse keyboard-layout-editor JSON format
        data = deserialise(json)
        self.keys, self.color = data['keys'], ImageColor.getrgb(data['meta']['backcolor'])
        self.keyboard = Image.new('RGB', (1000, 1000), color=self.color)
        self.max_size = (0, 0)


    def render(self):
        # choose size and scale of canvas depending on number of keys
        scale, border = min(int(len(self.keys) / 160 + 1), 5), 24

        # render each key
        for key in self.keys: self.render_key(key, scale, border)

        # watermark and crop the image
        self.max_size = [size + int(border / scale) for size in self.max_size]
        self.watermark_keyboard('Made with kle-render.herokuapp.com', scale)
        self.keyboard = self.keyboard.crop((0, 0, self.max_size[0], self.max_size[1]))
        return self.keyboard


    def render_key(self, key, scale, border):
        # render key and scale resulting image for subpixel accuracy
        key_img = key.render(scale, False)

        # paste in proper location and update max_size
        location = [coord + border for coord in key.get_location(key_img)]
        self.max_size = [max(location[2], self.max_size[0]), max(location[3], self.max_size[1])]
        self.expand_keyboard(scale)
        self.keyboard.paste(key_img, (location[0], location[1]), mask=key_img)


    def expand_keyboard(self, scale):
        if all(self.max_size[i] < self.keyboard.size[i] for i in range(2)): return
        new_size = tuple(int(size + 1000 / scale) for size in self.max_size)
        new_keyboard = Image.new('RGB', new_size, color=self.color)
        new_keyboard.paste(self.keyboard, (0, 0))
        self.keyboard = new_keyboard


    def watermark_keyboard(self, text, scale):
        # config margin size and watermark colors
        margin = int(18 / scale)
        background_color = ImageColor.getrgb('#202020')
        text_color = ImageColor.getrgb('#E0E0E0')

        # calculate size of watermark
        draw = ImageDraw.Draw(self.keyboard)
        font = ImageFont.truetype('fonts/SA_font.ttf', int(36 / scale))
        w, h = font.getsize(text)
        self.max_size = size = [max(w, self.max_size[0]), (self.max_size[1] + h + margin * 2)]

        # draw watermark bar below image
        draw.rectangle((0, size[1] - h - margin * 2, size[0] + 1, size[1] + 1), fill=background_color)
        draw.text((margin, size[1] - h - margin), text, font=font, fill=text_color)


def get_labels(key, fa_subs, kb_subs):
    # split into labels for each part of key
    labels = key.split('\n')
    for i, label in enumerate(labels):
        tree = lxml.html.fragment_fromstring(label, create_parent=True)
        # set key.pic to true and make label url of image
        if tree.xpath('//img[1]/@src'):
            return (tree.xpath('//img[1]/@src'), True)

        # replace icons with unicode characters
        for fa_icon in tree.find_class('fa'):
            fa_class = re.search(r'fa-\S+', fa_icon.get('class'))
            if fa_class and fa_class.group(0) in fa_subs:
                fa_icon.text = chr(int(fa_subs[fa_class.group(0)], 16))
        for kb_icon in tree.find_class('kb'):
            kb_class = re.search(r'kb-(\S+)', kb_icon.get('class'))
            if kb_class and kb_class.group(0) in kb_subs:
                kb_icon.text = chr(int(kb_subs[kb_class.group(0)], 16))

        # replace breaks with newlines and remove html entities
        for br in tree.xpath('//br'): br.text = '\n'
        labels[i] = html.unescape(tree.text_content())
    return (labels, False)


def deserialise(rows):
    # Initialize with defaults
    current = Key()
    meta, keys = {'backcolor': '#EEEEEE'}, []
    color_format = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
    default_size = current.label_sizes[0]
    with open('fonts/fa2unicode.json') as fa, open('fonts/kbd-webfont2unicode.json') as kb:
        fa_subs, kb_subs = json.load(fa), json.load(kb)

    for row in rows:
        if isinstance(row, list):
            for key in row:
                if isinstance(key, str):
                    newKey = copy.copy(current)
                    newKey.labels, newKey.pic = get_labels(key, fa_subs, kb_subs)
                    keys.append(newKey)

                    # Set up for the next key
                    current.x += current.width
                    current.width = current.height = 1.0
                    current.x2 = current.y2 = current.width2 = current.height2 = 0.0
                    current.pic = current.step = current.decal = False
                else:
                    if 'r' in key:
                        current.rotation_angle = key['r']
                    if 'rx' in key:
                        current.rotation_x = key['rx']
                        current.x = current.y = 0
                    if 'ry' in key:
                        current.rotation_y = key['ry']
                        current.y = current.y = 0
                    if 'a' in key:
                        current.align = int(key['a'])
                    if 'f' in key:
                        default_size = float(key['f'])
                        current.label_sizes = [default_size] * 12
                    if 'f2' in key:
                        current.label_sizes = [float(key['f2'])] * 12
                    if 'fa' in key:
                        label_sizes = [float(size) if size > 0 else default_size for size in key['fa']]
                        current.label_sizes = label_sizes[:12] + [default_size] * (12 - len(label_sizes)) 
                    if 'p' in key:
                        current.str_profile = key['p']
                    if 'c' in key:
                        color = key['c'].replace(';', '')
                        current.color = color if color_format.match(color) else current.color
                    if 't' in key:
                        colors = [line.replace(';', '') for line in key['t'].splitlines()]
                        default_color = colors[0] if color_format.match(colors[0]) else '#000'
                        colors = [color if color_format.match(color) else default_color for color in colors]
                        current.label_colors = colors[:12] + [default_color] * (12 - len(colors)) 
                    if 'x' in key:
                        current.x += float(key['x'])
                    if 'y' in key:
                        current.y += float(key['y'])
                    if 'w' in key:
                        current.width = float(key['w'])
                    if 'h' in key:
                        current.height = float(key['h'])
                    if 'x2' in key:
                        current.x2 = float(key['x2'])
                    if 'y2' in key:
                        current.y2 = float(key['y2'])
                    if 'w2' in key:
                        current.width2 = float(key['w2'])
                        current.height2 = current.height
                    if 'h2' in key:
                        current.height2 = float(key['h2'])
                        current.width2 = current.width if current.width2 == 0.0 else current.width2
                    if 'l' in key:
                        current.step = key['l']
                    if 'd' in key:
                        current.decal = key['d']
            # End of the row
            current.y += 1.0
        elif 'backcolor' in row:
            color = row['backcolor'].replace(';', '')
            meta['backcolor'] = color if color_format.match(color) else meta['backcolor']
        current.x = 0
    return {'meta': meta, 'keys': keys}
