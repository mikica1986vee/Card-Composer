# Card Composer
Helper script for automatic card arrangemet for printing. It supports custom paper and card size. Usefull for fast prototyping of customizable card games.

## Setup

Install [Python](https://www.python.org/) and [ImageMagick](https://www.imagemagick.org/).
Place (or symlink) card images to _card_images_ directory. You can use sub directories.
For every deck create file in _decks_ directory. On every newline you can use {{number of copies}} {{card name}}.
Assumed format for card names is '{{card number id}} - {{card name}}'. You can use card name only.
Quotes in card name are replaced with '\_' so keep that in mind.

## Usage

You can customize parameters from _config.ini_. You can create different _config.ini_ files.
From command line, call 'python compose_cards.py' to use default _config.ini_ file. To use different config file call 'python compose_cards.py your_config_file_name.ini'
