# wordpress-epub
Download articles from wordpress, convert to epub

## Requirements
 * Python 3.2 or newer
 * Install pip if needed https://pip.pypa.io/en/stable/installing/
 * Install libs:

     pip install cfscrape lxml beautifulsoup4 html5lib nodejs requests pyexecjs ebooklib


## Usage
Run download-chapters.py against a config file, then run make-epub.py against a
 config file

Example Shell code for updating all at once

    #!/bin/sh
    update_all() {
      local wpepub="$1";
      for c in $(find $wpepub/configs/ -iname '*.cfg'); do
        echo $c;
        (
          cd $wpepub/;
          python3 download-chapters.py $c;
          python3 make-epub.py $c;
        );
        echo;
      done;
    }
    update_all "$HOME/github/wordpress-epub/"
