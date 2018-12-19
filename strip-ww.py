#! /usr/bin/env python
# This is a quick and dirty to try and prep certain files for epub
# Requires:
#   Beautiful Soup 4, html5lib, lxml

import sys
import argparse
import lxml
import lxml.html
import lxml.etree
import os
import os.path
import re

def strip_file(argv=None):
  parser = argparse.ArgumentParser(description='Download web pages')
  parser.add_argument('input', help="specify input file to strip for ePub")
  if argv is None:
    argv = sys.argv
  args = parser.parse_args(argv[1:])

  raw_html = ""
  with open(args.input, 'r', encoding="utf-8") as html_file:
    raw_html = lxml.html.parse(html_file)

  epub_title = raw_html.xpath("//html/head/title")[0].text_content()
  epub_title = re.sub("^\s*[A-Z]+(\s*-\s*)?", "", epub_title)
  epub_title = re.sub("Chapter [0-9]+(\s*-\s*)?", "", epub_title)
  epub_title = re.sub("(\s*-\s*)?WuxiaWorld", "", epub_title)
  
  # skip down to just the body
  tree = lxml.etree.ElementTree(
    raw_html.xpath("//div[contains(@class, 'fr-view')]")[0])
  # pull out span tags while keeping contents
  for span in tree.findall("//span"):
    span.drop_tag()
  # Remove Previous/Next chapter links
  for link in tree.findall(".//a[@class]"):
    if link.get("class") != "chapter-nav":
      next
    link.drop_tree()
  epub_body = lxml.etree.tostring(tree)
  # pull out head.title and desired body
  # <div class="fr-view">
  ## completely remove element and text for a.class="chapter-nav"
  ## remove all <span style=""> but keep the text
  epub_html = """
<html>
 <head>
  <title>{TITLE}</title>
 </head>
 <body>
  <section epub:type="chapter">
{BODY}
  </section>
 </body>
</html>
""".format(TITLE=epub_title, BODY=str(epub_body, encoding='utf-8'))
  # Need to change extension of filename to xhtml
  epub_xhtml = "{}.xhtml".format(os.path.splitext(args.input)[0])
  with open(epub_xhtml, "w", encoding="utf-8") as xhtml_file:
    xhtml_file.write(
      str(
        lxml.etree.tostring(
          lxml.html.document_fromstring(epub_html),
          encoding='utf-8',
          pretty_print=True),
      encoding='utf-8'))

if __name__ == '__main__':
  if sys.hexversion < 0x03020000:
    sys.stderr.write("ERROR: Requires Python 3.2.0 or newer\n")
    sys.exit(1)
  sys.exit(strip_file())
