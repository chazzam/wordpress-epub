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
import sys
import argparse
import cfscrape
import os
import os.path
# ~ import pdb
import random
import requests
import time
import urllib.parse

# ~ from lxml import html, etree
# ~ from bs4 import BeautifulSoup, UnicodeDammit
from bs4 import BeautifulSoup

def locate_outfile(args=None, url=None, page=None):
  if args is None:
    return ""
  outfile = ""

  if args.output != "":
    # If args.output, it takes precedent
    outfile = args.output
  else:
    # default to the majority of the requested URL
    parsed = urllib.parse.urlsplit(url)
    outfile = parsed.geturl().replace(parsed.scheme, "").replace("://", "")

    # estimate the final filename
    if (args.adjust_extension
        and not outfile.lower().endswith(".html")
        and not outfile.lower().endswith(".htm")
        and (page is not None and "html" in page.headers.get('content-type')) or (page is None)):
      outfile += ".html"
    # trim off any requested top level directories
    if args.cut_dirs > 0:
      outfile = os.path.join(*outfile.lstrip("/").split("/")[args.cut_dirs:])
    if args.prefix != "":
      # Otherwise, check args.prefix and build the outfile up
      outfile = os.path.join(args.prefix, outfile)

  outfile = os.path.abspath(outfile)
  return outfile

def download_link(args=None):
  # Download a given chapter

  if (args.url is None or args.output is None):
    return 2

  url = args.url.strip()
  # If the first character of the url is /, then it should be relative
  if url[0] == "/":
    url = urllib.parse.urljoin(args.base, url.lstrip("/"))

  if args.no_clobber_early:
    outfile = locate_outfile(args, url)
    if os.path.isfile(outfile):
      print("Skipping existing file {} early".format(outfile))
      return 26

  # ~ url = urllib.parse.quote(url) # this is getting rid of the scheme
  if (args.scraper is not None):
    page = args.scraper.get(url)
  else:
    page = requests.get(url)
  if page.status_code == 404:
    print("ERROR: Downloading {} from {} failed.".format(
      args.filename, url))
    return 4

  # remove scripts from the download
  # TODO: Need to flag this on and off
  page.encoding="utf-8"
  tree = BeautifulSoup(page.text, "html5lib")
  for i in tree("script"):
    i.decompose()
  tree = BeautifulSoup(tree.html.prettify(formatter="html"), "html5lib")

  # note using page.url to use the final URL (after any redirects)
  outfile = locate_outfile(args, page.url, page)
  # Return true if we won't clobber
  if args.no_clobber and os.path.isfile(outfile):
    print("Skipping existing file {}".format(outfile))
    return 25
  # TODO: Add a check on timestamps vs page headers last modified for args.newer
  os.makedirs(os.path.dirname(outfile), exist_ok=True)

  with open(outfile, 'w') as f:
    f.write(tree.prettify(formatter="html"))
  # alternately:
  # ~ with open(filename, 'w') as f:
    # ~ f.write(page.content)
  print('Downloaded {} from {}'.format(outfile, page.url))
  return 0

def download_links(args=None):
  # Download links
  # Loop over lines in links file
  # download each with cfscraper and save to output directory
  if (args is None or args.input_file is None):
    print("ERROR: failed download")
    return False
  result = 0
  with open(args.input_file, 'r') as links:
    n_pass = False
    for line in links:
      url = line.strip()
      if url == "" or url[0] == "#":
        continue
      args.url = url
      raw_result = download_link(args)
      if raw_result == 26:
        # we skipped before making a request, so loop immediately
        continue
      elif raw_result != 25:
        result += raw_result
      if args.wait > 0 and n_pass:
        if args.random_wait:
          args.wait = random.randrange(0.5 * args.wait_orig, 1.5 * args.wait_orig)
        time.sleep(args.wait)
      n_pass = True
  return result


def main(argv=None):
  parser = argparse.ArgumentParser(description='Download web pages')
  parser.add_argument('--url', '-u',
    help="specify link to download")
  parser.add_argument('--input-file', '-i', default="",
    help="specify file of links, one per line")
  parser.add_argument('--output', '-O', default="",
    help="specify output file")
  parser.add_argument('--newer', '-N', action='store_true', default=False,
    help="don't overwrite unless newer (FIXME: currently the same as --no-clobber)")
  parser.add_argument('--no-clobber', '-nc', action='store_true', default=False,
    help="don't clobber existing files")
  parser.add_argument('--no-clobber-early', '-nce', action='store_true', default=False,
    help="skip clobbering based on initial URL, rather than actual requested URL, implies --no-clobber")
  parser.add_argument('--base', '-B', default="",
    help="Base URL for relative links")
  parser.add_argument('--prefix', '-P', default="",
    help="prefix directory for downloads")
  parser.add_argument('--cut-dirs', type=int, default=0,
    help="Ignore N directory components")
  parser.add_argument('--wait', '-w', type=int, default=0,
    help="Wait N seconds between requests")
  parser.add_argument('--random-wait', action='store_true', default=False,
    help="Wait 0.5 - 1.5 * <wait> between requests")
  parser.add_argument('--adjust-extension', '-E', action='store_true', default=False,
    help="Add .html extension if it doesn't exist on text/html mime")

  if argv is None:
    argv = sys.argv
  args = parser.parse_args(argv[1:])

  if args.random_wait:
    if args.wait <= 0:
      args.wait = 10
    args.wait_orig = args.wait
    random.seed()

  # no-clobber-early implies no-clobber
  if args.no_clobber_early:
    args.no_clobber = True

  # TODO: make newer actually timestamp based...
  if args.newer:
    args.no_clobber = True

  scraper = cfscrape.create_scraper()
  args.scraper = scraper
  result = True
  if args.input_file != "":
    return download_links(args)
  else:
    return download_link(args)



if __name__ == '__main__':
  if sys.hexversion < 0x03020000:
    sys.stderr.write("ERROR: Requires Python 3.2.0 or newer\n")
    sys.exit(1)
  sys.exit(main())
