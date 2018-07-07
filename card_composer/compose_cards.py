import os
from io import open
from shutil import copyfile
from shutil import rmtree
from subprocess import call
from subprocess import check_output

try:
    from ConfigParser import SafeConfigParser # for python 2.7
except ImportError:
    from configparser import SafeConfigParser # for python 3+

class MeasurementsData:
    
    def __init__(self, parser):
        self.unit = parser.get('measurements', 'unit')
        self.dpi = parser.getfloat('measurements', 'dpi')
        
        self.scale = 1.0
        
        if self.unit == 'in':
            self.scale = self.dpi
        
        elif self.unit == 'cm':
            self.scale = self.dpi / 2.54

class CardData:
    
    def __init__(self, parser):
        scale = MeasurementsData(parser).scale
        self.width = parser.getfloat('card', 'width') * scale
        self.height = parser.getfloat('card', 'height') * scale
        self.overlay_size = parser.getfloat('card', 'overlay_size') * scale
        self.overlay_color = parser.get('card', 'overlay_color')
        self.background_color = parser.get('card', 'background_color')
        
    def __str__(self):
        return 'width=' + str(self.width) + '\n' + 'height=' + str(self.height) + '\n' + 'overlay_size=' + str(self.overlay_size) + '\n' + 'overlay_color=' + str(self.overlay_color)

class ImageDatabase:
    def __init__(self, parser):
        self.image_path = parser.get('env', 'image_path')
        
        base_dir = self.image_path
        
        if not os.path.isdir(base_dir):
            base_dir = os.path.join(os.getcwd(), base_dir)
            
        print('reading images from ' + str(base_dir))
            
        self.database = {}
        self.recursive_load_images(self.database, base_dir)
        
    def recursive_load_images(self, map, current_path, ident = 0):
        if os.path.isdir(current_path):
            for f in os.listdir(current_path):
                ident_str = ''
                
                for i in range(ident):
                    ident_str += '\t'
                
                self.recursive_load_images(map, os.path.join(current_path, f), ident + 1)
                
            pass
        else:
            key = crop_filename(os.path.basename(current_path)).lower()
            if not key in map:
                map[key] = current_path
            pass
        pass
    
    def get_path(self, key):
        return self.database[key.lower()]
    
class DeckDatabase:
    
    def __init__(self, parser):
        self.decks = []
        
        base_dir = parser.get('deck', 'deck_path')
        
        if not os.path.isdir(base_dir):
            base_dir = os.path.join(os.getcwd(), base_dir)
            
        self.recursive_load_decks(self.decks, base_dir)
        
    def recursive_load_decks(self, decks, current_path):
        if os.path.isdir(current_path):
            for f in os.listdir(current_path):
                self.recursive_load_decks(decks, os.path.join(current_path, f))
        else:
            deck_name = key = os.path.basename(current_path)
            
            with open(current_path, 'r') as file:
                try:
                    decks.append(DeckData(deck_name, file.read()))
                except UnicodeDecodeError:
                    os.sys.exit('Invalid caracters detected in deck ' + deck_name + ', replace them with nearest ascii equivalent.')
    
    def __str__(self):
        text = ''
        
        for d in self.decks:
            text += 'Deck: ' + d.name + '\n'
            
            for c in d.cards:
                text += '\t' + str(c) + '\n'
                
        return text
        
    
class DeckData:
    
    def __init__(self, name, deck_str):
        self.name = name
        self.cards = []
        
        for s in deck_str.split('\n'):
            if len(s.strip()) == 0:
                continue
            
            self.cards.append(self._card_from_line(s))
        pass
    
    def _card_from_line(self, line):
        separator = line.find(' ')
        
        try:
            count = int(line[0 : separator].strip())
            name = line[separator : len(line)].strip()
        except:
            count = 1
            name = line.strip()
        
        return Card(name, count)
    
class Card:
    
    def __init__(self, name, count):
        self.name = name.replace("'", '_').replace('"', '_')
        self.count = count
        
    def __str__(self):
        return self.name + ': ' + str(self.count)
    
class SheetData:
    
    def __init__(self, parser):
        scale = MeasurementsData(parser).scale
        
        self.width = parser.getfloat('sheet', 'width') * scale
        self.height = parser.getfloat('sheet', 'height') * scale
        self.gap = parser.getfloat('sheet', 'gap') * scale
        self.dead_zone = parser.getfloat('sheet', 'dead_zone') * scale
        self.image_type = parser.get('sheet', 'image_type')
        
class Composer:
    def __init__(self, sheet_data, card_data):
        self.sheet_data = sheet_data
        self.card_data = card_data
        
        dw = (sheet_data.width - 2 * sheet_data.dead_zone) % (card_data.width + sheet_data.gap)
        dh = (sheet_data.height - 2 * sheet_data.dead_zone) % (card_data.height + sheet_data.gap)
        
        dw = dw // 2
        dh = dh // 2
        
        self.min_width = sheet_data.dead_zone + dw
        self.max_width = sheet_data.width - sheet_data.dead_zone -dw
        
        self.min_height = sheet_data.dead_zone + dh
        self.max_height = sheet_data.dead_zone + sheet_data.height - dh
        
    def __str__(self):
        return 'width: ' + str(self.min_width) + ' <-> ' + str(self.max_width) + '\nheight: ' + str(self.min_height) + ' <-> ' + str(self.max_height)
    
    def new_deck(self, name):
        self.current_name = name
        self.current_page = 0
        self.new_page()
        
    def new_page(self):
        self.current_page += 1
        self.current_width = self.min_width
        self.current_height = self.min_height
        
        self.current_path = os.path.join(output, self.current_name + '_' + str(self.current_page) + '.' + self.sheet_data.image_type)
        
        wxh = str(int(self.sheet_data.width)) + 'x' + str(int(self.sheet_data.height))
        
        call(convert + ' -size ' + wxh + ' canvas:white "' + self.current_path + '"')
        
    def add_image(self, image_path):
        if self.current_width + self.card_data.width + self.sheet_data.gap > self.max_width:
            self.current_height += self.card_data.height + self.sheet_data.gap
            self.current_width = self.min_width
            
            if self.current_height + self.card_data.height + self.sheet_data.gap > self.max_height:
                self.new_page()
                
        wxd = magick_wxd(self.card_data.width, self.card_data.height)
        offset = magick_offset(self.current_width, self.current_height)
        
        call(convert + ' "' + self.current_path + '" "' + image_path + '" -geometry ' + wxd + offset + ' -composite "' + self.current_path + '"', shell=True) 
        
        self.current_width += self.card_data.width + self.sheet_data.gap
    
def crop_filename(filename):
    start = filename.find('-')
    end = filename.rfind('.')
    return filename[start + 1 : end].strip()

def magick_wxd(width, height):
    return str(int(width)) + 'x' + str(int(height))

def magick_offset(x, y):
    return '+' + str(int(x)) + '+' + str(int(y))

## helper functions ##

def create_temp_dir(dir_name):
    if os.path.exists(dir_name):
        os.sys.exit('_temp directory exists!')
    
    os.makedirs(dir_name)
    
def create_output_dir(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    
def copy_image(orig_path, dest_dir, image_name):
    copy_path = os.path.join(dest_dir, image_name)
    copyfile(orig_path, copy_path)
    return  copy_path
    
def resize_image(card_data, image_path):
    width = str(int(card_data.width))
    height = str(int(card_data.height))
    background = card_data.background_color
    
    wxh = width + 'x' + height
    
    call(convert + ' "' + image_path + '" -resize ' + wxh + ' -background "' + background + '" -compose Copy -gravity center -extent ' + wxh + ' "' + image_path + '"', shell=True)
    
    pass

def apply_border(card_data, image_path):
    color = card_data.overlay_color
    width = str(int(card_data.overlay_size))
    wxh = width + 'x' + width
    
    call(convert + ' "' + image_path + '" -shave ' + wxh + ' "' + image_path + '"', shell=True)
    call(convert + ' "' + image_path + '" -bordercolor "' + color + '" -border ' + wxh + ' "' + image_path + '"', shell=True)
    
## options ##
def create_sets(sets_dir, temp_path, composer):
    base_dir = sets_dir
    
    if not os.path.isdir(sets_dir):
        base_dir = os.path.join(os.getcwd(), sets_dir)
            
    if os.path.isdir(base_dir):
        for f in os.listdir(base_dir):
            f_path = os.path.join(base_dir, f)
            
            if os.path.isdir(f_path):
                create_set(f, f_path, temp_path, composer)

def create_set(set_name, set_dir, temp_path, composer):
    composer.new_deck(set_name)
    _create_set(set_dir, temp_path, composer)
    
def _create_set(current_path, temp_path, composer):
    if not os.path.isdir(current_path):
        new_path = copy_image(current_path, temp_path, os.path.basename(current_path))
        card_data = composer.card_data
        
        resize_image(card_data, new_path)
        apply_border(card_data, new_path)
        
        composer.add_image(new_path)
    else:
        for f in os.listdir(current_path):
            _create_set(os.path.join(current_path, f), temp_path, composer)

## main ##

config_name = 'config.ini'

if len(os.sys.argv) > 1:
    config_name = os.sys.argv[1]

print('Current dir: ' + str(os.getcwd()))
print('Current config file name: ' + config_name)

config = SafeConfigParser()
config.read(config_name)

output = config.get('env', 'output_path')
print('Output path: ' + output)

convert = config.get('magick', 'convert')
print('Using convert: ' + str(convert))

card_data = CardData(config)

image_database = ImageDatabase(config)
deck_database = DeckDatabase(config)
sheet_data = SheetData(config)
composer = Composer(sheet_data, card_data)

create_output_dir(output)

temp_path = '_temp'

if config.get('env', 'validate_decks').strip() == 'true':
    print('Deck validation started')
    is_valid = True
    
    for d in deck_database.decks:
        print('Deck: ' + d.name)
        
        for c in d.cards:
            try:
                image_database.get_path(c.name)
            except KeyError:
                is_valid = False
                print('\t"' + c.name + '" not found.')
    
    if not is_valid:
        os.sys.exit('Missing or incorrect naming of cards.')

# start process
create_temp_dir(temp_path)

for d in deck_database.decks:
    composer.new_deck(d.name)
    
    for c in d.cards:
        print('Processing "' + c.name + '" from "' + image_database.get_path(c.name) + '"')
        new_path = copy_image(image_database.get_path(c.name), temp_path, c.name)
        resize_image(card_data, new_path)
        apply_border(card_data, new_path)
        
        for i in range(c.count):
            composer.add_image(new_path)
        
rmtree(temp_path)

print('Creating decks in pdf')

dpi = config.get('measurements', 'dpi').strip()
pdf_output = os.path.join(output, 'pdf')

create_output_dir(pdf_output)

for d in deck_database.decks:
    print('Creating ' + d.name + '.pdf')
    
    deck_image_path = os.path.join(output, d.name + '*')
    pdf_deck_path = os.path.join(pdf_output, d.name + '.pdf')
    
    call('magick -density ' + dpi + ' ' + deck_image_path + ' ' + pdf_deck_path) 

print('Done')