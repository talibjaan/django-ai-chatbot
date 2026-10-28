import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    )
}


def extract_page_content(url):
    """
    Fetch one webpage and extract readable text.
    """

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove elements that usually don't contain useful page content
        for element in soup([
            "script",
            "style",
            "noscript",
            "svg",
            "iframe",
            "nav",
            "footer"
        ]):
            element.decompose()

        title = soup.title.get_text(strip=True) if soup.title else ""

        text = soup.get_text(
            separator=" ",
            strip=True
        )

        return {
            "url": url,
            "title": title,
            "text": text
        }

    except requests.RequestException as e:
        return {
            "error": str(e)
        }


def get_internal_links(url, html):
    """
    Find links belonging to the same website.
    """

    soup = BeautifulSoup(html, "html.parser")

    base_domain = urlparse(url).netloc

    links = set()

    for link in soup.find_all("a", href=True):

        href = link["href"]

        absolute_url = urljoin(url, href)

        parsed = urlparse(absolute_url)

        if parsed.netloc == base_domain:

            clean_url = absolute_url.split("#")[0]

            links.add(clean_url)

    return links


def analyze_website(url, max_pages=10):
    """
    Crawl a website and collect readable content.
    """

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    visited = set()
    pages_to_visit = [url]
    website_content = []

    while pages_to_visit and len(visited) < max_pages:

        current_url = pages_to_visit.pop(0)

        if current_url in visited:
            continue

        visited.add(current_url)

        try:

            response = requests.get(
                current_url,
                headers=HEADERS,
                timeout=15
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            for element in soup([
                "script",
                "style",
                "noscript",
                "svg",
                "iframe",
                "nav",
                "footer"
            ]):
                element.decompose()

            title = (
                soup.title.get_text(strip=True)
                if soup.title
                else current_url
            )

            text = soup.get_text(
                separator=" ",
                strip=True
            )

            if text:

                website_content.append({
                    "url": current_url,
                    "title": title,
                    "text": text
                })

            # Find more internal pages
            for link in soup.find_all("a", href=True):

                next_url = urljoin(
                    current_url,
                    link["href"]
                )

                parsed = urlparse(next_url)

                if (
                    parsed.netloc == urlparse(url).netloc
                    and next_url not in visited
                ):
                    next_url = next_url.split("#")[0]

                    if next_url not in pages_to_visit:
                        pages_to_visit.append(next_url)

        except requests.RequestException:
            continue

    return website_content