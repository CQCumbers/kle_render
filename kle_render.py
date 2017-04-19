from PIL import Image, ImageColor
from key import Key
import copy, html

def render_keyboard(data):
    border = 24
    keys = data['keys']
    max_x = max([key.rough_location()[2] for key in keys]) + 2*border
    max_y = max([key.rough_location()[3] for key in keys]) + 2*border
    if len(data['meta']) > 0:
        c = ImageColor.getrgb(data['meta']['backcolor'])
    else:
        c = ImageColor.getrgb('#000000')
    keyboard = Image.new('RGBA', (max_x, max_y), color=c)
    for key in keys:
        key_img = key.render()
        location = [int(coord+border) for coord in key.location(key_img)]
        keyboard.paste(key_img, (location[0], location[1]), mask=key_img)
    return keyboard.resize((int(max_x/3), int(max_y/3)), resample=Image.LANCZOS) #Lanczos is high quality downsampling algorithm

def deserialise(rows): # where rows is a dictionary version of Keyboard Layout Editor's JSON Output
    # Initialize with defaults
    current = Key()
    meta = { 'backcolor': '#eeeeee' }
    keys = []
    cluster = { 'x': 0.0, 'y': 0.0 }
    for row in rows:
        if isinstance(row, list):
            for key in row:
                if isinstance(key, str):
                    newKey = copy.copy(current);
                    newKey.width2 = current.width if newKey.width2 == 0.0 else current.width2
                    newKey.height2 = current.height if newKey.height2 == 0.0 else current.height2
                    newKey.labels = [html.unescape(text) for text in key.replace('<br>', '\n').split('\n')]
                    keys.append(newKey)

                    # Set up for the next key
                    current.x += current.width
                    current.width = current.height = 1.0
                    current.x2 = current.y2 = current.width2 = current.height2 = 0.0
                    current.nub = current.stepped = current.stepped = current.decal = False
                else:
                    if 'r' in key:
                        current.rotation_angle = key['r']
                        current.y = 0
                    if 'rx' in key:
                        current.rotation_x = cluster['x'] = key['rx']
                    if 'ry' in key:
                        current.rotation_y = cluster['y'] = key['ry']
                    if 'a' in key:
                        current.align = key['a']
                    if 'f' in key:
                        current.font_size = current.font_size2 = float(key['f'])
                    if 'f2' in key:
                        current.font_size2 = float(key['f2'])
                    if 'p' in key:
                        current.profile = key['p']
                    if 'c' in key:
                        current.color = key['c'].replace(';', '')
                    if 't' in key:
                        current.font_color = key['t'].replace(';', '')
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
                    if 'h2' in key:
                        current.height2 = float(key['h2'])
                    if 'n' in key:
                        current.nub = key['n']
                    if 'l' in key:
                        current.stepped = key['l']
                    if 'g' in key:
                        current.ghost = key['g']
                    if 'd' in key:
                        current.decal = key['d']
            # End of the row
            current.y += 1.0;
        elif 'backcolor' in row:
            meta['backcolor'] = row['backcolor'].replace(';', '')
        current.x = 0 #current.rotation_x
    return {'meta': meta, 'keys': keys}
