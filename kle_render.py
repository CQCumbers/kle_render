from PIL import Image, ImageColor, ImageDraw, ImageFont
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
    if len(keys) < 25:
        scale = 2
    elif len(keys) < 200:
        scale = 3
    elif len(keys) < 540:
        scale = 4
    else:
        scale = 5
    s = (160 * 0.97**len(keys) + 40 + 2*border)*len(keys)
    keyboard = Image.new('RGB', (int(round(s/scale)),int(round(s/scale))), color=c)
    max_x = max_y = 0

    pool = ThreadPool(16) # hopefully avoid running out of threads on heroku
    pool.map(render_key, keys)
    pool.close() 
    pool.join()

    max_x += int(round(border/scale))
    max_y += int(round(border/scale))
    keyboard = watermark(keyboard)
    keyboard = keyboard.crop((0, 0, max_x, max_y))
    return keyboard

def render_key(key):
    global max_x, max_y
    key_img = key.render()
    location = [int((coord+border)/scale) for coord in key.location(key_img)]
    paste_img = Image.new('RGBA', tuple([int(i/scale+2)*scale for i in key_img.size]))
    paste_img.paste(key_img, tuple([coord % scale for coord in key.location(key_img)[:2]]), mask=key_img)
    max_x = max(location[2], max_x)
    max_y = max(location[3], max_y)
    paste_img = paste_img.resize(tuple([int(i/scale) for i in paste_img.size]), resample=Image.LANCZOS)
    keyboard.paste(paste_img, (location[0], location[1]), mask=paste_img)

def watermark(img):
    global max_x, max_y
    text = 'Made with kle-render.herokuapp.com'
    margin = 5
    c1 = ImageColor.getrgb('#202020')
    c2 = ImageColor.getrgb('#E0E0E0')

    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype('SA_font.ttf', 12)
    w, h = font.getsize(text)
    max_x = max(int(w/scale), max_x)
    max_y += h + 2*margin

    draw.rectangle((0, max_y-h-margin*2, max_x+1, max_y+1), fill=c1)
    draw.text((margin, max_y-h-margin), text, font=font, fill=c2)

    return img

def html_to_unicode(html): # unescaped html input
    cleanr = re.compile(r'<.*?>')
    with open('fa2unicode.json') as data1:
        d = json.load(data1)
    with open('kbd-webfont2unicode.json') as data2:
        d2 = json.load(data2)
    pattern = re.compile('|'.join(('<i class=[\'\"]fa ({})[\'\"]></i>'.format(icon) for icon in d.keys()))) # I know, re's and html...
    pattern2 = re.compile('|'.join(('<i class=[\'\"]kb kb-({})[\'\"]></i>'.format(icon) for icon in d2.keys())))

    result = pattern.sub(lambda x: chr(int(d[x.group()[13:-6]], 16)), html)
    result = pattern2.sub(lambda x: chr(int(d2[x.group()[16:-6]], 16)), result)
    result = result.replace('<br>', '\n').replace('<br/>', '\n').replace('','') # last one is a unicode control char
    result = re.sub(cleanr, '', result)
    return result

def deserialise(rows): # where rows is a dictionary version of Keyboard Layout Editor's JSON Output
    # Initialize with defaults
    current = Key()
    default_font_size = current.font_size[0]
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
                        default_font_size = float(key['f'])
                        current.font_size = [default_font_size] * 9
                    if 'f2' in key:
                        current.font_size = [float(key['f2'])] * 9
                    if 'fa' in key:
                        current.font_size = [float(key['fa'][i]) if i < len(key['fa']) and key['fa'][i] > 0 else default_font_size for i in range(9)]
                    if 'p' in key:
                        current.profile = key['p']
                    if 'c' in key:
                        current.color = key['c'].replace(';', '')
                    if 't' in key:
                        f_colors = [''.join(c for c in line if c in '0123456789abcdefABCDEF#') for line in key['t'].splitlines()]
                        f_colors = [color for color in f_colors if color_format.match(color) or not color.strip()] # more gracefully handle invalid colors
                        if len(f_colors) > 0:
                            current.font_color = f_colors
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
