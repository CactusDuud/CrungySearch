import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin

LINKS_EXPLORED = set()
BAD_LINKS = set()


def scraper(url, resp):
    links = extract_next_links(url, resp)
    valid_links = [link for link in links if is_valid(link)]
    print("Finished processing,", len(LINKS_EXPLORED), "valid links,", len(BAD_LINKS), "bad links")
    print()
    return valid_links


def extract_next_links(url, resp):
    """
    url: the URL that was used to get the page
    resp.url: the actual url of the page
    resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was
        some kind of problem.
    resp.error: when status is not 200, you can check the error here, if needed.
    resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
            resp.raw_response.url: the url, again
            resp.raw_response.content: the content of the page!
    Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    """
    # Ensure the page responds and is not empty
    valid_page = resp.status == 200 and resp.raw_response is not None and resp.raw_response.content is not None

    print(resp.url + " - " + str(valid_page))

    '''parsed = urlparse(resp.url)
    path = parsed.path.lower().split("/")
    if len(path) > 0:
        TRASH.add(parsed.netloc + "/" + path[-1])'''

    links_in = set()
    links = []
    if valid_page:
        LINKS_EXPLORED.add(resp.url)
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
        for l in soup.find_all('a', href=True):
            link = str(urljoin(resp.url, l['href'])).split("#")[0].split("?")[0]
            if link not in links_in:
                links_in.add(link)
                links.append(link)
    else:
        BAD_LINKS.add(resp.url)

    return links


def is_valid(url: str) -> bool:
    """
    Decide whether to crawl this url or not.
    
    :param url: The url to analyse, as a string
    :return: True to crawl this url, False otherwise
    """
    try:
        parsed = urlparse(url)

        # Check if we've seen this site
        if url in LINKS_EXPLORED or url in BAD_LINKS:
            return False

        # Troublesome sites are bad >:(
        if "share=facebook" in parsed.path.lower() or \
                "share=twitter" in parsed.path.lower() or \
                "replytocom" in parsed.path.lower() or \
                "/ml/machine-learning-databases" in parsed.path.lower() or \
                "anyconnect" in parsed.path.lower() or \
                "stayconnected" in parsed.path.lower():
            return False

        # Ensure the url has the correct scheme
        if parsed.scheme not in {"http", "https"}:
            return False

        # Check if this url is within our domains
        if not re.match(
                r".*\.ics\.uci\.edu|"
                r".*\.cs\.uci\.edu|"
                r".*\.informatics\.uci\.edu|"
                r".*\.stat\.uci\.edu|"
                r"today\.uci\.edu/department/information_computer_sciences",
                parsed.netloc):
            return False

        # Check if the path of this url is something we can read
        if re.match(
                r".*\.(css|js|bmp|gif|jpe?g|ico|png|tiff?|mid|mp[2-4]|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf|ps|eps|"
                r"tex|pptx?|docx?|xlsx?|names|data?|exe|bz2|tar|msi|bin|7z|psd|dmg|iso|epub|dll|cnf|tgz|sha1|thmx|mso|"
                r"arff|rtf|jar|csv|rm|smil|wmv|swf|wma|zip|rar|gz)$",
                parsed.path.lower()):
            return False

        clean_path = parsed.path.lower().split("/")
        if len(clean_path) >= 8:  #if more than 8 nested folders in path
            return False

        path_seen = set()
        for p in clean_path:  #check for duplicate folders in path
            if p in path_seen:
                return False
            path_seen.add(p)

        '''#check for duplicate file, limited to main domains
        if parsed.netloc in ["www.ics.uci.edu", "www.cs.uci.edu", "www.informatics.uci.edu", "www.stat.uci.edu"]:
            if len(clean_path) > 0 and parsed.netloc + "/" + clean_path[-1] in TRASH:
                return False'''

        # Check if this site is similar to the current one

        return True

    except TypeError:
        print("TypeError for ", parsed)
        raise
