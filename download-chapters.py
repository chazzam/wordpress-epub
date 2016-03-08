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

# Requires:
#   Beautiful Soup 4, Requests, html5lib, PyExecJS, cfscrape, nodejs
import queue, threading

def download_chapter(
  url=None, filename=None,
  main_title=None, title_strip=None, title_re=None, scraper=None
):
  # Download a given chapter
  from lxml import html, etree
  from bs4 import BeautifulSoup, UnicodeDammit
  import requests, re
  #~ import pdb

  #~ pdb.set_trace()
  if (url is None or filename is None):
    return False

  if (scraper is not None):
    page = scraper.get(url)
  else:
    page = requests.get(url)
  if page.status_code == 404:
    return False
  page.encoding="utf-8"
  #tree = BeautifulSoup(UnicodeDammit.detwingle(page.text), "html5lib")
  tree = BeautifulSoup(page.text, "html5lib")
  # Trim down to just the article content
  title = ""
  btree = tree.article
  if not btree:
    return False
  # remove Next/Previous
  for i in btree("a", string=re.compile(
    "(Next|Prev(ious)?|Index|TOC|Table of Contents)( ?Chapter)?")
  ):
    i.decompose()
  #~ for i in btree("a", string="Previous Chapter"):
    #~ i.decompose()
  for i in btree("hr"):
    i.unwrap()
  for i in btree("script"):
    i.decompose()
  for i in btree("span", style=re.compile("float: ?right")):
    i.decompose()
  for i in btree("span", style=re.compile("(font-family|color|text-align)")):
    i.unwrap()
  for i in btree("div", class_=re.compile("wpcnt|sharedaddy|code-block")):
    i.decompose()
  for i in btree("p"):
    if 'style' in i:
      del i['style']
  if "Previous Chapter" in btree.p.text:
    btree.p.decompose()
  # TODO: remove all empty tags
  # Want to rewrite chapter links
  # pull images from glossary page and embed?
  if (main_title is not None and main_title != ""):
    title = main_title
  else:
    doc_title = btree.find("h1", class_="entry-title")
    temp_string = ""
    if doc_title and isinstance(doc_title, list):
      doc_title = doc_title[0]
    if doc_title:
      for x in doc_title.stripped_strings:
        temp_string = "{} {}".format(temp_string, x)
    doc_title = temp_string
    if ("glossary" in doc_title.lower() or
      "index" in doc_title.lower()
    ):
      title = doc_title
    else:
      t_div = btree("div", class_="entry-content")[0]
      if (t_div.u):
        t_div.u.unwrap()
      if t_div.span:
        t_div.span.unwrap()
      if t_div.br:
        t_div.br.decompose()
      if (t_div.b):
        st = tree.new_tag("strong")
        temp_string = ""
        for x in t_div.b.stripped_strings:
          temp_string = temp_string + " {}".format(x)
        st.string = temp_string
        tree.article.div.b.replace_with(st)
      titles = t_div.strong
      #~ print("titles:{}".format(titles))
      if (titles):
        if titles.br:
          titles.br.decompose()
        if not titles.string:
          title = ""
          for x in titles.stripped_strings:
            title = title + " {}".format(x)
        else:
          title = titles.string
        #~ print("strtitle:{}".format(title))
        if (re.match('^\s+$', title)):
          title = ""
      if (title == "" and t_div.h3):
        title = t_div.h3.string
        #~ print("h3title:{}".format(title))
      if (title == ""):
        title = doc_title
        #~ print("dtitle:{}".format(title))
    if not title:
      title = tree.title.string
    #~ print("title:{}".format(title))
    title = title.strip()
    title = re.sub(re.compile('\n|  |\r|\t|&nbsp;'), ' ', title)
    title = title.replace('  ', ' ')
    if (title_strip is not None):
      #~ print("strip:'{}' title:'{}'".format(title_strip, title))
      #title = title.replace(title_strip, '').strip()
      title = re.sub(title_strip, '', title).strip()
      #~ print("stripped:'{}'".format(title))
    if (title_re is not None):
      title_re = title_re.strip()
      title_re = title_re.rstrip('"')
      title_re = title_re.lstrip('"')
      title_re = title_re.rstrip("'")
      title_re = title_re.lstrip("'")
      t_regex = title_re.split('||')
      title = re.sub(t_regex[0], t_regex[1], title)
      #~ print("re:'{}' title:'{}'".format(title_re,title))
  nt = tree.new_tag("section")
  nt["epub:type"] = "chapter"
  tmp = tree.article("div", class_="entry-meta")
  if tmp:
    tmp[0].decompose()
  tree.article.div.wrap(nt)
  tree.article.div.unwrap()
  nt = tree.new_tag("body")
  tree.article.section.wrap(nt)
  nt = tree.new_tag("html")
  tree.article.section.wrap(nt)
  nt = tree.new_tag("head")
  tree.article.section.insert_before(nt)
  nt = tree.new_tag("title")
  nt.string = title.strip()
  tree.article.head.append(nt)
  nt = tree.new_tag("link", rel="stylesheet", href="style/main.css")
  nt["type"] = "text/css"
  tree.article.head.append(nt)
  #~ tree = html.fromstring(big_html)
  #~ html.html_to_xhtml(tree)
  tree = BeautifulSoup(tree.article.html.prettify(formatter="html"), "html5lib")
  with open(filename, 'w') as f:
    f.write(tree.prettify(formatter="html"))
      #~ elif (line.tag == 'em'):
#~ # http://www.wuxiaworld.com/issth-index/issth-book-3-chapter-267
        #~ # ignore emote sponsored by lines
    # support footnotes
    #http://www.idpf.org/accessibility/guidelines/content/xhtml/notes.php
# http://www.wuxiaworld.com/issth-index/issth-book-3-chapter-268
#  <p>“Black Lands Dao Children Luo Chong and Xu Fei!” <sup class='footnote'><a href='#fn-31821-1' id='fnref-31821-1' onclick='return fdfootnote_show(31821)'>1</a></sup></p>
#~ <div class='footnotes' id='footnotes-31821'>
#~ <div class='footnotedivider'></div>
#~ <ol>
#~ <li id='fn-31821-1'> Luo Chong’s name in Chinese is 罗冲 luó chōng &#8211; Luo is a surname which also means “sieve” or “net.” Chong means “charge” or “clash.” Xu Fei’s name in Chinese is 徐菲 Xú fēi &#8211; Xu is a common surname which also means “gentle” or “slow.” Fei means “humble” <span class='footnotereverse'><a href='#fnref-31821-1'>&#8617;</a></span></li>
#~ </ol>
#~ </div>
#~ </div>

def worker():
  global q
  #~ import pdb
  import cfscrape
  scraper = cfscrape.create_scraper()
  while True:
    item = q.get()
    #~ pdb.set_trace()
    if item is None:
      break
    rs = download_chapter(url=item[0], filename=item[1],
      main_title=item[2], title_strip=item[3],
      title_re=item[4], scraper=scraper)
    q.task_done()
    if rs == False:
      print("ERROR: Downloading {} from {} failed.".
        format(item[1], item[0])
      )
    else:
      print('Downloaded {} from {}'.format(item[1], item[0]))

def main(argv=None):
  from sys import argv as sys_argv
  from os.path import join, abspath, isfile
  from os import makedirs
  import configparser, argparse
  parser = argparse.ArgumentParser(description='Download Light Novel Chapters')
  parser.add_argument('config', help="specify config file")
  parser.add_argument('--output', '-o', help="specify output directory")
  parser.add_argument('--update-all', '-U', action='store_true', help="Update all files")
  parser.add_argument('--workers', '-w', type=int, default=3,
    help="number of thread workers to run")

  if argv is None:
    argv = sys_argv
  args = parser.parse_args(argv[1:])
  config = configparser.SafeConfigParser()
  try:
      config.read(args.config)
  except configparser.Error:
      print("ERROR: Could not parse config file: {0}".format(args.config))
      return 1
  if ( (not config.has_section('toc')) or
    (not config.has_option('toc', 'order'))
  ):
    print("ERROR: Config file does not have proper table of contents [toc] section")
    return 1
  order = config.get('toc', 'order').split(',')
  if not config.has_section('TITLES'):
    config.add_section('TITLES')
  if (config.has_option('DEFAULT', 'chapter-directory') and
    (args.output == "" or args.output is None)
  ):
    args.output = config.get('DEFAULT', 'chapter-directory')
  makedirs(abspath(args.output), exist_ok=True)
  global q
  q = queue.Queue()
  threads = []
  for i in range(args.workers):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)
  files_list = set()
  for sec in order:
    sec = sec.strip()
    if not config.has_section(sec):
      continue
    # build filename
    if not (config.has_option(sec, 'chapter-file') or
      config.has_option(sec, 'chapter-files')
    ):
      print('Skipping section "{}": no "chapter-file"'.format(sec))
      continue
    title_strip = None
    title_regrep = None
    if (config.has_option(sec, 'title_strip')):
      title_strip = config.get(sec, 'title_strip')
    if (config.has_option(sec, 'title_re')):
      title_regrep = config.get(sec, 'title_re')
    if (config.has_option(sec, 'chapters')):
      ch_urls = config.get(sec, 'chapters').split(',')
      ch_files = config.get(sec, 'chapter-files').split(',')
      if (len(ch_urls) != len(ch_files)):
        print('Skipping section "{}": mismatched chapters/file'.format(sec))
        continue
      for i in range(0, len(ch_urls)):
        ch_url = ch_urls[i].strip()
        ch_file = ch_files[i].strip()
        ch_title = None
        filename = join(abspath(args.output), ch_file)
        if ( (isfile(filename) or filename in files_list) and
          not args.update_all
        ):
          continue
        files_list.add(filename)
        if (config.has_option('TITLES', ch_file)):
          ch_title = config.get('TITLES', ch_file)
        q.put((ch_url, filename, ch_title, title_strip, title_regrep))
    for x in [('start', 'end'), ('end', 'start')]:
      if (config.has_option(sec, x[0]) and not config.has_option(sec, x[1])):
        config.set(sec, x[1], config.get(sec, x[0]))
    if (config.has_option(sec, 'start') and config.has_option(sec, 'end')):
      sec_start = config.get(sec, 'start')
      sec_end = config.get(sec, 'end')
      if (sec_start == "" and sec_end == ""):
        continue
      if (sec_start == "" and sec_end != ""):
        sec_start = sec_end
      if (sec_end == "" and sec_start != ""):
        sec_end = sec_start
      sec_start = int(sec_start)
      sec_end = int(sec_end)
      ch_range = range(sec_start, sec_end + 1)
      ch_url = config.get(sec, 'chapter-url')
      ch_parts = list()
      vol = 1
      if (config.has_option(sec, 'volume')):
        vol = config.get(sec, 'volume')
      range_skips = set()
      if (config.has_option(sec, 'skip_download')):
        tmp_skips = config.get(sec, 'skip_download').strip().split(',')
        for x in range(0, len(tmp_skips)):
          tmp_skips[x] = tmp_skips[x].strip()
        range_skips.update(tmp_skips)
      if (config.has_option(sec, 'part')):
        ch_parts = config.get(sec, 'part').strip().split(',')
        for x in range(0, len(ch_parts)):
          ch_parts[x] = ch_parts[x].strip()
      else:
        ch_parts = [0]
      ch_file = config.get(sec, 'chapter-file').strip()
      for ch_num in ch_range:
        if (str(ch_num) in range_skips):
          continue
        for ch_part in ch_parts:
          ch_file_filled = ch_file.format(
            volume=vol, chapter=ch_num, part=ch_part
          )
          ch_filename = join(abspath(args.output), ch_file_filled)
          ch_title = None
          if ( (isfile(ch_filename) or ch_filename in files_list) and
            not args.update_all
          ):
            continue
          files_list.add(ch_filename)
          #~ download_chapter(
            #~ ch_url.format(volume=vol, chapter=ch_num),
            #~ ch_filename
          #~ )
          if (config.has_option('TITLES', ch_file_filled)):
            ch_title = config.get('TITLES', ch_file_filled)
          q.put((ch_url.format(volume=vol, chapter=ch_num, part=ch_part),
            ch_filename, ch_title, title_strip, title_regrep)
          )
  print(q.qsize())
  q.join()
  for i in range(args.workers):
    q.put(None)
  for t in threads:
    t.join()
  if len(files_list) == 0:
    # Nothing to do, return 200 (OK), for chaining commands together
    return 200
  return 0
  # parse sections as defined by order
  # within a section
  # Check if given chapter-file already exists, and skip unless UPDATE-ALL
  # check for 'chapters' and download those
  # if has start & end, download those (inclusive) with chapter-url
  # save chapters to chapter-file

if __name__ == '__main__':
  from sys import exit, hexversion
  if hexversion < 0x03020000:
    sys.stderr.write("ERROR: Requires Python 3.2.0 or newer\n")
    exit(1)
  exit(main())
