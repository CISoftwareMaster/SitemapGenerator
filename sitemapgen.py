import re
import sys
import signal
import xml.etree.cElementTree as xml
from datetime import datetime
from urllib.request import urlopen
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from termcolor import colored


# compile our regexp patterns
full_stop = False
pattern = re.compile("[A-Za-z]+\.[A-Za-z]+\.[A-Za-z]+")
strip = re.compile("\#.+")


class Link:
    # this is our crawler link class
    def __init__(self, title, url):
        self.title = title
        self.url = url


# handle interrupt events
def interrupt(signal, frame):
    print(colored(
        "\nFuture crawl processes will be canceled, however all current tasks must finish first before this application could finish.\n", "yellow"))
    full_stop = True

# check if a link is unique
def is_unique(url: str, url_pool: list) -> bool:
    for link in url_pool:
        if link.url == url:
            return False
    return True


# get base URL
def base_url_of(url):
    return pattern.findall(url)[0]


# our main crawler function
def crawl(url, baseurl=None, links=[], level=0, exclude_base=False, silent=False):
    # formulate our base URL
    if baseurl is None:
        baseurl = url

    passed_checks = False

    # check if this URL matches our base URL
    x = base_url_of(baseurl)
    y = base_url_of(url)

    if x == y and not full_stop:
        # check if a URL is provided
        if url is not None:
            # try to load the target document
            try:
                with urlopen(url) as target:
                    # parse the document using beautiful soup
                    document = BeautifulSoup(target.read(), "html.parser")
                    # get this webpage's title
                    title = document.find("title").getText()
                    # find our links
                    doclinks = document.findAll("a")

                    # insert this to our link collection
                    if not exclude_base or (exclude_base and not level == 0):
                        links.append(Link(title, url))

                    # iterate through our link collection
                    for link in doclinks:
                        link_url = urljoin(baseurl, link.get("href"))

                        # strip unnecessary URL extensions
                        extras = strip.findall(link_url)
                        if extras is not None and len(extras) > 0:
                            link_url = link_url.replace(extras[0], "")

                        # check if it's unique
                        if is_unique(link_url, links):
                            if not silent:
                                print("Crawling %s..." % link_url)
                            # crawl this link
                            crawl(link_url, baseurl, links, level+1, exclude_base, silent)
            except:
                if not silent:
                    print("Crawl error: can't reach \"%s\"" % url)
    else:
        if not silent:
            print("Crawl error: \"%s\" failed the same-domain check!" % url)

    # check if we are at our "base" level
    if level == 0:
        # return our links
        return links


# our main directive
if __name__ == "__main__":
    # check argument count
    if len(sys.argv) >= 3:
        # register our interrupt handler
        signal.signal(signal.SIGINT, interrupt)

        sitemapfile = sys.argv[2]

        if len(sys.argv) >= 4:
            silentmode = (sys.argv[3] == "--silent" or sys.argv[3] == "-s")
        else:
            silentmode = False

        # create the root of our sitemap
        root = xml.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

        # get current date
        date = datetime.now()

        # create our "lastmod" property
        moddate = "%04d-%02d-%02d" % (date.year, date.month, date.day)

        # crawl the main URL we provided
        links = crawl(sys.argv[1], silent=silentmode)

        print(colored("\n<----- showing crawled links ------>\n", "green"))
        for link in links:
            # print a crawled link here
            print(link.title + "\t" + link.url)

            # create a new "url" node in our sitemap
            node = xml.SubElement(root, "url")

            # populate properties
            xml.SubElement(node, "loc").text = link.url
            xml.SubElement(node, "lastmod").text = moddate
            xml.SubElement(node, "changefreq").text = "monthly"
            xml.SubElement(node, "priority").text = str(1.0)

        # write our sitemap to file
        xml.ElementTree(root).write(sitemapfile)
        print(colored(
            "Your sitemap has been written to \"%s\"." % sitemapfile, "green"))
    else:
        # otherwise, show how our program is used
        print("Usage: python3 sitemapgen.py [main URL] [output file]")
        print("To silence crawler logs, add at the end of the command \"--silent\" or \"-s\"")
