import os
from datetime import datetime
import logging
import warnings
from functools import wraps

import requests

from .google import get_search_results

"""
Copyright 2019 Simon Caine

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

logger = logging.getLogger(__name__)


headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36"
}


class SearchWarning(UserWarning):
    pass


def results_summary(search_num, title, link, base_dir="output"):
    """
    save the search_num, title and link text
    to a summary file as we go
    """

    os.makedirs(base_dir, exist_ok=True)
    summary_file = os.path.join(base_dir, "results_summary.csv")
    if not os.path.isfile(summary_file):
        with open(summary_file, "w", encoding="utf-8") as fid:
            fid.writelines(f"search number, title, link\n")

    with open(summary_file, "a", encoding="utf-8") as fid:
        fid.writelines(f"{str(search_num).zfill(3)}, {title}, {link}\n")


def save_pdf(search_num, link, base_dir="output", timeout=60):
    """
    given a pdf link download the pdf into a subfolder
    based on the search number
    """

    save_dir = os.path.join(base_dir, f"{str(search_num).zfill(3)}")
    os.makedirs(save_dir, exist_ok=True)
    fname = os.path.join(save_dir, os.path.basename(link))
    logger.info(f"attempting to download {fname}")

    try:
        page = requests.get(link, allow_redirects=True, headers=headers, timeout=60)
        page.raise_for_status()
        with open(fname, "wb") as fid:
            fid.write(page.content)
        logger.info(f"    {fname} saved")
    except requests.exceptions.HTTPError:
        logger.error(f"link does not exit")
        write_fail_msg(fname, link)
    except requests.exceptions.Timeout as e:
        logger.warning(f"download failed with error {e}")
        write_timeout_msg(fname, link)
    except Exception as e:
        logger.warning(f"download failed with error {e}")
        write_generic_fail_msg(fname, link)


def write_timeout_msg(fname, link):
    """
    Create a file in liew of the correct one that lets the user
    know the request timed out and include link so they can manually
    download the file.

    This can happen if the pdf file is quite large or the internet
    connection is a bit dodgy
    """

    os.makedirs(os.path.dirname(fname), exist_ok=True)

    with open(fname + ".timedout.txt", "w", encoding="utf-8") as fid:
        msg = (
            "timed out when trying to download,"
            " please manually download using the link below\n"
            f"{link}"
        )
        fid.writelines(msg)


def write_fail_msg(fname, link):
    """
    Create a file in liew of the correct one that lets the user
    know the requested link does not exist
    """

    os.makedirs(os.path.dirname(fname), exist_ok=True)

    with open(fname + ".404error.txt", "w", encoding="utf-8") as fid:
        msg = "recieved 404 error when trying to download\n" f"{link}"
        fid.writelines(msg)


def write_generic_fail_msg(fname, link):
    """
    Create a file in liew of the correct one that lets the user
    know the requested download/save failed
    """

    os.makedirs(os.path.dirname(fname), exist_ok=True)

    with open(fname + ".failed.txt", "w", encoding="utf-8") as fid:
        msg = "recieved an error when trying to download\n" f"{link}"
        fid.writelines(msg)


def save_link(search_num, link, base_dir="output"):
    """
    given a link that we are not going to download, save the
    link to a text file so the user knows what the link was
    """

    save_dir = os.path.join(base_dir, f"{str(search_num).zfill(3)}")
    os.makedirs(save_dir, exist_ok=True)
    fname = os.path.join(save_dir, "website_link.txt")
    logger.info(f"saving link to {fname}")

    with open(fname, "w", encoding="utf-8") as fid:
        fid.writelines(link)


def get_webpage(url, results=100, base_dir="output"):
    # to do, warn that we cannot have results > 100
    if results > 100:
        warnings.warn(
            SearchWarning(
                "More than 100 search results not implemented, setting to 100"
            )
        )
        results = 100

    url += f"&num={results}"
    webpage = requests.get(url, headers=headers)
    save_google_search(url, webpage.text, base_dir=base_dir)
    return webpage.text


def save_google_search(url, webpage_text, base_dir="output"):
    os.makedirs(base_dir, exist_ok=True)
    fname = os.path.join(base_dir, "google-search-term.txt")
    with open(fname, "w", encoding="utf-8") as fid:
        fid.write(url)

    fname = os.path.join(base_dir, "google-search-result.html")
    with open(fname, "w", encoding="utf-8") as fid:
        fid.write(webpage_text)


def search_and_download(url, results=100):  # pragma: no cover
    search_time = f"{datetime.utcnow():%Y%m%d_%H%M%S}"
    webpage = get_webpage(url, results=results, base_dir=search_time)
    if "scholar.google" in url:
        search = "scholar"
    else:
        search = "google"

    for indx, search in enumerate(get_search_results(webpage, search=search)):
        results_summary(indx, search.title, search.primary_link, base_dir=search_time)
        if search.do_download:
            save_pdf(indx, search.primary_link, base_dir=search_time)
        else:
            save_link(indx, search.primary_link, base_dir=search_time)
