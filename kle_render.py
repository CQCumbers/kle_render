from PIL import Image, ImageColor
from multiprocessing.dummy import Pool as ThreadPool
from key import Key
import copy, html, re, json

border = 24
keyboard = None
scale = 3

def render_keyboard(data):
    global keyboard
    global max_x, max_y
    global scale
    keys = data['keys']
    if len(data['meta']) > 0:
        c = ImageColor.getrgb(data['meta']['backcolor'])
    else:
        c = ImageColor.getrgb('#000000')
    if len(keys) < 10:
        scale = 1
    elif len(keys) < 200:
        scale = 3
    elif len(keys) < 540:
        scale = 4
    else:
        scale = 5
    s = (160 * 0.97**len(keys) + 40 + 2*border)*len(keys)
    #s = len(keys) * 300 # DEBUG
    keyboard = Image.new('RGBA', (int(round(s/scale)),int(round(s/scale))), color=c)
    max_x = max_y = 0

    pool = ThreadPool(16) # hopefully avoid running out of threads on heroku
    pool.map(render_key, keys)
    pool.close() 
    pool.join()
    keyboard = keyboard.crop((0, 0, max_x + int(round(border/scale)), max_y + int(round(border/scale))))
    return keyboard

def render_key(key):
    global max_x, max_y
    key_img = key.render()
    location = [int((coord+border)/scale) for coord in key.location(key_img)]
    max_x = max(location[2], max_x)
    max_y = max(location[3], max_y)
    key_img = key_img.resize(tuple([int(i/scale)+1 for i in key_img.size]), resample=Image.LANCZOS) # Lanczos is high quality downsampling algorithm
    keyboard.paste(key_img, (location[0], location[1]), mask=key_img)

def html_to_unicode(html): # unescaped html input
    cleanr = re.compile(r'<.*?>')
    with open('fa2unicode.json') as data1:
        d = json.load(data1)
    with open('kbd-webfont2unicode.json') as data2:
        d2 = json.load(data2)
    pattern = re.compile('|'.join(("<i class='fa {}'></i>".format(icon) for icon in d.keys()))) # I know, re's and html...
    pattern2 = re.compile('|'.join(("<i class='kb kb-{}'></i>".format(icon) for icon in d2.keys())))

    result = pattern.sub(lambda x: chr(int(d[x.group()[13:-6]], 16)), html)
    result = pattern2.sub(lambda x: chr(int(d2[x.group()[16:-6]], 16)), result)
    result = result.replace('<br>', '\n').replace('<br/>', '\n')
    return re.sub(cleanr, '', result)

def deserialise(rows): # where rows is a dictionary version of Keyboard Layout Editor's JSON Output
    # Initialize with defaults
    current = Key()
    meta = { 'backcolor': '#eeeeee' }
    keys = []
    color_format = re.compile(r'#[a-fA-F0-9]{3}(?:[a-fA-F0-9]{3})?$')

    for row in rows:
        if isinstance(row, list):
            for key in row:
                if isinstance(key, str):
                    newKey = copy.copy(current);
                    newKey.labels = [html_to_unicode(text) for text in html.unescape(key).split('\n')]
                    keys.append(newKey)

                    # Set up for the next key
                    current.x += current.width
                    current.width = current.height = 1.0
                    current.x2 = current.y2 = current.width2 = current.height2 = 0.0
                    current.nub = current.stepped = current.stepped = current.decal = False
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
                        current.font_size = current.font_size2 = float(key['f'])
                    if 'f2' in key:
                        current.font_size2 = float(key['f2'])
                    if 'p' in key:
                        current.profile = key['p']
                    if 'c' in key:
                        current.color = key['c'].replace(';', '')
                    if 't' in key:
                        f_color = key['t'].replace(';', '').replace('\n', '')
                        if '#' in f_color[1:]: # hack to prevent multiple font colors from causing crash
                            f_color = f_color[:4]
                        if color_format.match(f_color): # more gracefully handle invalid colors
                            current.font_color = f_color
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
                        if current.width2 == 0.0:
                            current.width2 = current.width
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
        elif 'backcolor' in row and len(row['backcolor']) > 0:
            meta['backcolor'] = row['backcolor'].replace(';', '')
        current.x = 0 #current.rotation_x
    return {'meta': meta, 'keys': keys}
