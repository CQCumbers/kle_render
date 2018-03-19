import copy, html, lxml.html, re, json, functools
from PIL import Image, ImageColor, ImageDraw, ImageFont
from multiprocessing.dummy import Pool as ThreadPool
from key import Key


class Keyboard_Render:
    __slots__ = ['data', 'keyboard', 'max_size']


    def __init__(self, json):
        # parse keyboard-layout-editor JSON format
        self.data = self.deserialise(json)


    def render(self):
        # choose size and scale of canvas depending on number of keys
        keys = self.data['keys']
        c = ImageColor.getrgb(self.data['meta']['backcolor'])
        if len(keys) < 25:
            scale = 2
        elif len(keys) < 200:
            scale = 3
        elif len(keys) < 540:
            scale = 4
        else:
            scale = 5
        border = 24
        s = (160 * 0.97**len(keys) + 40 + 2 * border) * len(keys)
        self.keyboard = Image.new('RGB', (int(round(s / scale)), int(round(s / scale))), color=c)
        self.max_size = (0, 0)

        # render each key using multiprocessing
        pool = ThreadPool(16)
        pool.map(functools.partial(self.render_key, scale=scale, border=border), keys)
        pool.close()
        pool.join()

        # watermark and crop the image
        self.max_size = [size + int(round(border / scale)) for size in self.max_size]
        self.watermark_keyboard('Made with kle-render.herokuapp.com', scale=scale)
        self.keyboard = self.keyboard.crop((0, 0, self.max_size[0], self.max_size[1]))
        return self.keyboard


    def render_key(self, key, scale=2, border=0):
        # render key and scale resulting image for subpixel accuracy
        key_img = key.render()
        scaled_img = Image.new('RGBA', tuple(int(i / scale + 2) * scale for i in key_img.size))
        scaled_img.paste(key_img, tuple(coord % scale for coord in key.get_location(key_img)[:2]), mask=key_img)
        scaled_img = scaled_img.resize(tuple(int(i / scale) for i in scaled_img.size), resample=Image.LANCZOS)

        # paste in proper location and update max_size
        location = [int((coord + border) / scale) for coord in key.get_location(key_img)]
        self.max_size = [max(location[2], self.max_size[0]), max(location[3], self.max_size[1])]
        self.keyboard.paste(scaled_img, (location[0], location[1]), mask=scaled_img)


    def watermark_keyboard(self, text, scale=2):
        # config margin size and watermark colors
        margin = 5
        background_color = ImageColor.getrgb('#202020')
        text_color = ImageColor.getrgb('#E0E0E0')

        # calculate size of watermark
        draw = ImageDraw.Draw(self.keyboard)
        font = ImageFont.truetype('fonts/SA_font.ttf', 12)
        w, h = font.getsize(text)
        self.max_size = size = [max(int(w / scale), self.max_size[0]), (self.max_size[1] + h + 2 * margin)]

        # draw watermark bar below image
        draw.rectangle((0, size[1] - h - margin * 2, size[0] + 1, size[1] + 1), fill=background_color)
        draw.text((margin, size[1] - h - margin), text, font=font, fill=text_color)


    def get_labels(self, key, fa_subs, kb_subs):
        # split into labels for each part of key
        labels = key.split('\n')
        for i in range(len(labels)):
            tree = lxml.html.fragment_fromstring('<div>' + labels[i] + '</div>')
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

            # replace breaks with newlines and remove control char
            for br in tree.xpath('//br'):
                br.text = '\n'
            labels[i] = tree.text_content().replace('<90>', '')
        return (labels, False)
    

    def deserialise(self, rows):
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
                        newKey.labels, newKey.pic = self.get_labels(key, fa_subs, kb_subs)
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
