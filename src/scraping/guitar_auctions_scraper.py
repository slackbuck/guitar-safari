"""
TODO:
- Set up langfuse tracking for this scraper.
- Set up db (postgress container) to store scraped data.
- Set up API keys for LLM usage.
- Set up logging instead of print statements.
- Add error handling for network requests and parsing.
- Modularize code into functions for better readability and maintainability.
- Add typer
"""

from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

from src.scraping.base_scraper import BaseScraper

class GuitarAuctionScraper(BaseScraper):

    def __init__(self, base_url= "https://www.guitar-auctions.co.uk"):
        super().__init__(base_url)

    def get_lot_links(self, html_content, base_url):
        """
        Extracts and returns a list of full URLs to lot detail pages from the preview page HTML.
        
        Now, each lot is contained in a <div> with classes "cell large-3 medium-3 small-12"
        and the lot link is the href of the <a> tag within that cell.
        """
        soup = BeautifulSoup(html_content, "lxml")
        lot_links = []
        
        # Find all lot cells based on the known classes
        lot_cells = soup.find_all("div", class_="cell large-3 medium-3 small-12")
        for cell in lot_cells:
            a_tag = cell.find("a")
            if a_tag and a_tag.get("href"):
                full_url = urljoin(base_url, a_tag["href"])
                lot_links.append(full_url)
        
        return lot_links


    # def parse_lot_page(html):
    #     """
    #     Parses a lot detail page's HTML and returns a dictionary with:
    #     - 'description': The detailed guitar description.
    #     - 'estimate': The price estimate.
        
    #     This function assumes the detailed lot page contains a 
    #     <div class="cell large-7 medium-3 small-12"> that holds the description,
    #     and a <p> tag with text that includes "Estimate:".
    #     """
    #     soup = BeautifulSoup(html, "lxml")
        
    #     # Extract the container with the detailed description
    #     container = soup.find("div", class_="cell large-7 medium-3 small-12")
    #     description = ""
    #     if container:
    #         # Get the text node directly within the container
    #         description_node = container.find(string=True, recursive=False)
    #         if description_node:
    #             description = description_node.strip()
        
    #     # Extract the price estimate from a <p> tag containing "Estimate:"
    #     estimate_tag = soup.find("p", string=lambda text: text and "Estimate:" in text)
    #     estimate = estimate_tag.get_text(strip=True) if estimate_tag else "Not found"
        
    #     return {"description": description, "estimate": estimate}


    # def parse_lot_data(lot_data):
    #     # Initialize a dictionary for results.
    #     result = {}

    #     estimate = lot_data["estimate"]
    #     match = re.search(r"£(\d+)-(\d+)", estimate)
    #     if match:
    #         estimate_low = int(match.group(1))   # 3500
    #         result["estimate_low"] = estimate_low
    #         estimate_high = int(match.group(2))  # 5000
    #         result["estimate_high"] = estimate_high

    #     description = lot_data["description"]
    #     result["full_description"] = description

    #     body, *notes = description.split("*")

    #     if notes:
    #         result["notes"] = [note.strip() for note in notes if note.strip()]

    #     # Split the description on semicolons.
    #     parts = [part.strip() for part in body.split(";") if part.strip()]
        
    #     # The first part is the main description.
    #     if parts:
    #         summary = parts[0]
    #         # result["summary"] = summary
    #         # Optionally, use regex to extract the year if present.
    #         match = re.match(r"^(?P<year>\d{4})\s+(?P<title>.+)$", summary)
    #         if match:
    #             result["year"] = match.group("year")
    #             result["title"] = match.group("title")
    #         else:
    #             result["title"] = summary

    #         # Use the LLM to parse the title and merge response into results
    #         result = result | parse_title_with_llm(result["title"])

    #         # Look for a "made in" phrase in the summary.
    #         made_in_match = re.search(r"made in\s+([^,;]+)", summary, re.IGNORECASE)
    #         if made_in_match:
    #             result["made_in"] = made_in_match.group(1).strip()
        
    #     # Define the expected keys.
    #     keys = ["body", "neck", "fretboard", "frets", "electrics", "hardware", "case", "weight", "overall condition"]

    #     # Process each remaining part.
    #     for part in parts[1:]:
    #         # Look for the key: value pattern.
    #         if ":" in part:
    #             key, value = part.split(":", 1)
    #             key = key.strip().lower()  # normalize key to lowercase
    #             value = value.strip()
    #             if key == "weight":
    #                 value = float(value.replace("kg", ""))
    #             # Only save if the key is one of our expected keys.
    #             if key in keys:
    #                 result[key] = value
    #             else:
    #                 # If key not found in expected list, add to notes.
    #                 result.setdefault("notes", []).append(part)
    #         else:
    #             # If no colon, treat it as an additional note.
    #             result.setdefault("notes", []).append(part)
        
    #     return result


    # base_url = "https://www.guitar-auctions.co.uk"
    # preview_base_url = urljoin(
    #     base_url,
    #     "https://www.guitar-auctions.co.uk/sale/249/the-guitar-auction-(december)---day-one")

    # page = 1
    # all_lot_urls = []

    # while True:
    #     # Construct the URL: first page without query parameter, subsequent pages with ?page=
    #     if page == 1:
    #         preview_url = preview_base_url
    #     else:
    #         preview_url = f"{preview_base_url}?page={page}"

    #     print(f"Fetching page {page}: {preview_url}")
    #     preview_html = fetch_page(preview_url)
    #     if not preview_html:
    #         print("Could not fetch the preview page.")
    #         break


    #     # Extract links to individual lot detail pages using the revised approach
    #     lot_urls = get_lot_links(preview_html, base_url)
    #     if not lot_urls:
    #         print(f"No lot links found on page {page}. Assuming this is the last page.")
    #         break

    #     print(f"Found {len(lot_urls)} lot(s).")
    #     all_lot_urls.extend(lot_urls)
    #     page += 1

    # print(f"Total lot URLs found: {len(all_lot_urls)}")

    # scraped_data = []

    # # Process each lot: fetch detail page and parse the description and estimate.
    # for idx, lot_url in enumerate(all_lot_urls, start=1):
    #     print(f"\nProcessing Lot {idx}: {lot_url}")
    #     lot_html = fetch_page(lot_url)
    #     if lot_html:
    #         lot_data = parse_lot_page(lot_html)
    #         print("Description:", lot_data["description"])
    #         print("Estimate:", lot_data["estimate"])
    #         parsed_lot_data = parse_lot_data(lot_data)
    #         llm_valuation = get_llm_valuation(lot_data["description"])
    #         try:
    #             parse_lot_data_and_valuation = parsed_lot_data | llm_valuation[0]
    #             scraped_data.append([lot_url, parse_lot_data_and_valuation])
    #         except Exception as e:
    #             print(f"Failed to merge parsed lot data and valuation: {e}")
    #     else:
    #         print("Failed to fetch the lot page.")
    #     # if idx >= 10:
    #     #     break