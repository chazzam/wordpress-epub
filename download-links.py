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

def locate_outfile(args=None, url=None, strict=True):
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
        and ((not outfile.lower().endswith(".html")
          and not outfile.lower().endswith(".htm")
          and ('page_headers' in args
              and args.page_headers is not None
              and "html" in args.page_headers.get('content-type', "missing")))
        or not strict)):
      outfile += ".html"

    # trim off any requested top level directories
    if args.cut_dirs > 0:
      outfile = os.path.join(*outfile.lstrip("/").split("/")[args.cut_dirs:])

    if args.prefix != "":
      # Check args.prefix and build the outfile up
      outfile = os.path.join(args.prefix, outfile)

  outfile = os.path.abspath(outfile)
  return outfile

def scrape_page(args=None, url=None):
  if (args is None or url is None):
    return None

  # ~ url = urllib.parse.quote(url) # this is getting rid of the scheme
  if (args.scraper is not None):
    page = args.scraper.get(url)
  else:
    print("Falling back on requests for {}".format(url))
    page = requests.get(url)

  if page.status_code == 404:
    print("ERROR: Downloading from {} failed.".format(url))
    return None

  # remove scripts from the download
  # TODO: Need to flag this on and off
  page.encoding="utf-8"
  tree = BeautifulSoup(page.text, "html5lib")

  args.current_url = page.url
  args.page_headers = page.headers

  return tree

def phantom_page(args, url):
  if (args is None or url is None):
    return None

  tree = None
  try:
    import selenium
    import selenium.webdriver.support.ui

    if args.phantomjs is None:
      args.phantomjs = selenium.webdriver.PhantomJS()
      # ~ args.phantomwait = selenium.webdriver.support.ui.WebDriverWait(args.phantomjs, 10)

    args.phantomjs.get(url)
    time.sleep(10)
    # ~ if args.phantomjs.status == 404:
      # ~ print("ERROR: Downloading from {} failed.".format(url))
      # ~ return None

    tree = BeautifulSoup(args.phantomjs.page_source, "html5lib")

    # Fake it 'til you make it? :[
    try:
      args.current_url = args.phantomjs.current_url
    except:
      print("  Couldn't get current url, using original")
      args.current_url = url

    try:
      args.page_headers = args.phantomjs.page_headers
    except:
      print("  Couldn't get page headers, faking content-type:text/html")
      args.page_headers = {"content-type":"text/html"}
    args.phantomjs.close()

  except ModuleNotFoundError:
    return None

  return tree

def download_link(args=None):
  # Download a given chapter

  if (args is None or args.url is None or args.output is None):
    return 2

  url = args.url.strip()
  # If the first character of the url is /, then it should be relative
  if url[0] == "/":
    url = urllib.parse.urljoin(args.base, url.lstrip("/"))

  if args.no_clobber_early:
    outfile = locate_outfile(args, url, False)
    if os.path.isfile(outfile):
      print("Skipping existing file {} early".format(outfile))
      return 26

  if not args.phantom:
    tree = scrape_page(args, url)
  else:
    tree = phantom_page(args, url)
  if tree is None:
    return 4

  for i in tree("script"):
    i.decompose()
  tree = BeautifulSoup(tree.html.prettify(formatter="html"), "html5lib")

  # note using args.current_url to use the final URL (after any redirects)
  outfile = locate_outfile(args, args.current_url)
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

  print('Downloaded {} from {}'.format(outfile, args.current_url))
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
    requests_count = 0

    for line in links:
      url = line.strip()

      if url == "" or url[0] == "#":
        continue

      if requests_count % 500 == 0 and not args.phantom:
        args.scraper = cfscrape.create_scraper(sess=None)

      print("{:04d}: ".format(requests_count), end='')
      args.url = url

      # Attempt to delete the scraper and try again if it fails
      try:
        raw_result = download_link(args)
      except:
        args.scraper = None
        time.sleep(10)
        args.scraper = cfscrape.create_scraper(sess=None)
        raw_result = download_link(args)
      requests_count += 1

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
  parser.add_argument('--phantom', action='store_true', default=False,
    help="Use PhantomJS to download the page")

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

  if args.phantom:
    args.phantomjs = None

  args.page_headers = {}

  result = 1
  if args.input_file != "":
    result = download_links(args)
  else:
    args.scraper = cfscrape.create_scraper()
    result = download_link(args)

  if args.phantom and args.phantomjs is not None:
    args.phantomjs.quit()

  return result

if __name__ == '__main__':
  if sys.hexversion < 0x03020000:
    sys.stderr.write("ERROR: Requires Python 3.2.0 or newer\n")
    sys.exit(1)
  sys.exit(main())
