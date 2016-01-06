#! /usr/bin/env python
#This file is part of wordpress-epub.
#
#wordpress-epub is free software: you can redistribute it and/or modify
#it under the terms of the GNU Lesser General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#wordpress-epub is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU Lesser General Public License for more details.
#
#You should have received a copy of the GNU Lesser General Public License
#along with wordpress-epub.  If not, see <http://www.gnu.org/licenses/>.

from ebooklib import epub
import configparser

def ebook_init(config):
  ebook = epub.EpubBook()
  sec = 'toc'
  ebook.set_identifier(config.get(sec, 'id'))
  ebook.set_title(config.get(sec, 'title'))
  ebook.set_language(config.get(sec, 'language'))
  for auth in config.get(sec, 'author').split(','):
    ebook.add_author(auth)
  return ebook

def give_css(config):
  # return the css style sheet
  if (config.has_option('toc', 'css')):
    with open(config.get('toc', 'css'), 'r') as f:
      read_data = f.read()
    return read_data
  return """
  @namespace epub "http://www.idpf.org/2007/ops";

  body {
      font-family: Verdana, Helvetica, Arial, sans-serif;
  }

  h1 {
      text-align: center;
  }

  h2 {
      text-align: left;
      text-transform: uppercase;
      font-weight: 200;
  }

  ol {
      list-style-type: none;
      margin: 0;
  }

  ol > li {
      margin-top: 0.3em;
  }

  ol > li > span {
      font-weight: bold;
  }

  ol > li > ol {
      margin-left: 0.5em;
  }
  """

def give_intro(config):
  # return the Introduction
  if (config.has_option('toc', 'intro')):
    with open(config.get('toc', 'intro'), 'r') as f:
      read_data = f.read()
    return read_data
  return """
  <html>
  <head>
      <title>Introduction</title>
      <link rel="stylesheet" href="style/main.css" type="text/css" />
  </head>
  <body>
      <h1>{}</h1>
      <p><b>By: {}</b></p>
      <p>{}</p>
  </body>
  </html>
  """.format(
    config.get('toc', 'title'),
    config.get('toc', 'author'),
    config.get('toc', 'synopsis')
  )

def extract_chapter(chapter):
  from lxml import html
  # open the chapter file, return contents as string
  with open(chapter, 'r') as f:
    read_data = f.read()
  tree = html.fromstring(read_data)
  title = tree.xpath('//title/text()')[0]
  return (title.strip(), read_data)

def main(argv=None):
  from sys import argv as sys_argv
  from os.path import join, abspath, isfile, exists, basename
  from os import remove
  import argparse
  parser = argparse.ArgumentParser(description='Generate epub from Light Novel Chapters')
  parser.add_argument('config', help="specify config file")
  parser.add_argument('--input', '-i', help="specify input directory")

  if argv is None:
    argv = sys_argv
  args = parser.parse_args(argv[1:])
  config = configparser.SafeConfigParser()
  try:
      config.read(args.config)
  except configparser.Error:
      return 1
  if not config.has_section('toc'):
    return 1
  if not config.has_option('toc', 'order'):
    return 1
  if (config.has_option('DEFAULT', 'chapter-directory') and
    (args.input == "" or args.input is None)
  ):
    args.input = config.get('DEFAULT', 'chapter-directory')
  order = config.get('toc', 'order').split(',')
  ebook = ebook_init(config)
  doc_style = epub.EpubItem(
    uid="doc_style",
    file_name="style/min.css",
    media_type="text/css",
    content=give_css(config)
  )
  ebook.add_item(doc_style)
  
  intro_ch = epub.EpubHtml(title="Introduction", file_name="intro.xhtml")
  intro_ch.add_item(doc_style)
  intro_ch.content = give_intro(config)
  ebook.add_item(intro_ch)

  toc = [epub.Link('intro.xhtml', 'Introduction', 'intro')]
  chapters = []
  included_files = set()
  for sec in order:
    sec = sec.strip()
    if not config.has_section(sec):
      continue
    sec_chapters = []
    sec_title = config.get(sec, 'title')
    sec_start = ""
    sec_end = ""
    skip_explicit_chapters = False
    if (config.has_option(sec, 'chapters')):
      ch_files = config.get(sec, 'chapter-files').split(',')
      if (config.has_option(sec, 'epub_skip_chapters')):
        skip_explicit_chapters = config.getboolean(sec, 'epub_skip_chapters')
        # Skip processing explicit chapters when requested
      for ch_file in ch_files:
        if skip_explicit_chapters:
          continue
        ch_file = ch_file.strip()
        filename = join(abspath(args.input), ch_file)
        if (not isfile(filename)):
          continue
        if filename in included_files:
          continue
        ch_title, ch_content = extract_chapter(filename)
        ch = epub.EpubHtml(title=ch_title, file_name=ch_file)
        ch.add_item(doc_style)
        ch.content = ch_content
        ebook.add_item(ch)
        sec_chapters.append(ch)
        included_files.add(filename)
    if (config.has_option(sec, 'start')):
      sec_start = config.get(sec, 'start').strip()
    if (config.has_option(sec, 'end')):
      sec_end = config.get(sec, 'end').strip()
    if (sec_start == "" or sec_end == ""):
      if (sec_start == ""):
        sec_start = sec_end
      else:
        sec_end = sec_start
    if (sec_start != "" and sec_end != ""):
      sec_start = int(sec_start)
      sec_end = int(sec_end)
      ch_range = range(sec_start, sec_end + 1)
      vol = 1
      if (config.has_option(sec, 'volume')):
        vol = config.get(sec, 'volume')
      x_file = config.get(sec, 'chapter-file')
      for ch_num in ch_range:
        ch_file = x_file.format(volume=vol, chapter=ch_num)
        filename = join(abspath(args.input), ch_file)
        if (not isfile(filename)):
          continue
        if filename in included_files:
          continue
        ch_title, ch_content = extract_chapter(filename)
        ch = epub.EpubHtml(title=ch_title.strip(), file_name=ch_file)
        ch.add_item(doc_style)
        ch.content = ch_content
        ebook.add_item(ch)
        sec_chapters.append(ch)
        included_files.add(filename)
    if (len(sec_chapters) >= 1):
      if sec_title:
       toc.append((epub.Section(sec_title),sec_chapters))
      else:
       toc.extend(sec_chapters)
    #~ elif (len(sec_chapters) == 1):
      #~ toc.append(epub.Link(ch_file, ch_title, basename(ch_file)))
    chapters.extend(sec_chapters)
  ebook.toc = toc
  ebook.add_item(epub.EpubNcx())
  #ebook.add_item(epub.EpubNav())
  nav_page = epub.EpubNav(uid='book_toc', file_name='toc.xhtml')
  nav_page.add_item(doc_style)
  ebook.add_item(nav_page)
  ebook.spine = [intro_ch, nav_page] + chapters
  epub_filename = config.get('toc', 'epub')
  if exists(epub_filename):
    remove(epub_filename)
  epub.write_epub(epub_filename, ebook, {})
  
if __name__ == '__main__':
  from sys import exit, hexversion
  if hexversion < 0x03020000:
    sys.stderr.write("ERROR: Requires Python 3.2.0 or newer\n")
    exit(1)
  exit(main())
