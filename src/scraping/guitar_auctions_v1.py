"""
Old version of guitar auctions scraper, kept for reference only.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import gspread
from google.oauth2.service_account import Credentials
import os
import openai
import json
from dotenv import load_dotenv
import re
import langfuse
from langfuse.decorators import observe
# from langfuse.openai import openai

load_dotenv()


langfuse = langfuse.Langfuse(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)

def fetch_page(url):
    """Fetches a webpage and returns its HTML content."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def get_lot_links(html_content, base_url):
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

def parse_lot_page(html):
    """
    Parses a lot detail page's HTML and returns a dictionary with:
      - 'description': The detailed guitar description.
      - 'estimate': The price estimate.
      
    This function assumes the detailed lot page contains a 
    <div class="cell large-7 medium-3 small-12"> that holds the description,
    and a <p> tag with text that includes "Estimate:".
    """
    soup = BeautifulSoup(html, "lxml")
    
    # Extract the container with the detailed description
    container = soup.find("div", class_="cell large-7 medium-3 small-12")
    description = ""
    if container:
        # Get the text node directly within the container
        description_node = container.find(string=True, recursive=False)
        if description_node:
            description = description_node.strip()
    
    # Extract the price estimate from a <p> tag containing "Estimate:"
    estimate_tag = soup.find("p", string=lambda text: text and "Estimate:" in text)
    estimate = estimate_tag.get_text(strip=True) if estimate_tag else "Not found"
    
    return {"description": description, "estimate": estimate}

# TODO: verify docstring still relevant
def call_llm_for_json(system: str, prompt: str, model="gpt-4o-mini", temperature=0.0) -> dict:
    """
    Sends the provided prompt to the LLM and returns its response as a JSON object.
    
    Parameters:
      prompt (str): The prompt to send.
      model (str): The model to use (default is gpt-4o-mini).
      temperature (float): Sampling temperature.
    
    Returns:
      dict: Parsed JSON response from the LLM.
    """
    openai.api_key = os.getenv("OPENAI_API_KEY")

    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user","content": prompt}
            ],
            temperature=temperature
        )

        answer = response.choices[0].message
        data = json.loads(answer.content)
        return data, response


    except Exception as e:
        print(f"Error calling LLM: {e}")
        return {}

# TODO: verify docstring still relevant
# @observe()
def parse_title_with_llm(title):
    """
    Uses an LLM to extract 'brand', 'model', and 'type' from a guitar title.
    
    Expected output format:
      {"brand": <brand>, "model": <model>, "type": <type>}
    
    Only uses the following list for the "type" field:
      electric, acoustic, hollow body electric, seven string.
    If the guitar type in the title does not match any of these, return "other" for the type.
    """
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    system = "You are an assistant that extracts structured guitar details from a title."
    prompt = f"""
        Extract the following fields from the guitar title and return a valid JSON object with keys "brand", "model", and "type".
        Only use the following set of values for the "type" field: {{electric, hollow body electric, acoustic, bass}}.
        If the guitar type in the title does not match any of these, return "other" for the type.

        Examples:
        Title: "Epiphone Les Paul Standard electric guitar"
        Output: {{"brand": "Epiphone", "model": "Les Paul Standard", "type": "electric"}}

        Title: "Gibson EB-5 five string bass guitar, made in USA"
        Output: {{"brand": "Gibson", "model": "EB-5", "type": "electric"}}

        Title: "Lowden F22 acoustic guitar, made in Ireland"
        Output: {{"brand": "Lowden", "model": "F22", "type": "acoustic"}}

        Title: "Heritage H-575 hollow body electric guitar, made in USA"
        Output: {{"brand": "Heritage", "model": "H-575", "type": "hollow body electric"}}

        Now, extract the fields from the following title:
        "{title}"

        RETURN ONLY A VALID JSON WITH THE SPECIFIED KEYS."""

    trace =  langfuse.trace(
        name="parse_title_with_llm",
        input={"args": [title], "kwargs": {}}
    )

    generation = trace.generation(
        name="OpenAI-generation",
        model="gpt-4o-mini",
        input=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    )

    parsed_data, response = call_llm_for_json(prompt, system)

    generation.end(
        output=response.choices[0].message.content,
        usage_details=response.usage
    )

    # Log successful result
    trace.update(
        output=parsed_data,
        status="success"
    )
    return parsed_data


# TODO: verify docstring still relevant
@observe()
def get_llm_valuation(guitar_description: str) -> dict:
    """
    Builds a prompt to evaluate a guitar's second-hand market value and calls the LLM.
    
    The prompt instructs the LLM to return a JSON object with:
      - value_estimate_low: (integer) the lower end of the valuation in £,
      - value_estimate_high: (integer) the higher end of the valuation in £,
      - rationale: a brief explanation (max 250 characters).
      
    Parameters:
      guitar_info (str): The details of the guitar to evaluate.
      
    Returns:
      dict: The parsed JSON response with valuation details.
    """
    system = "You are a market analyst who provides valuations for guitars"
    prompt = f"""
        You are a market analyst specialized in evaluating guitars.
        Evaluate the second-hand market value for the following guitar details:
        {guitar_description}

        Your valuation should:
            - Focus on the UK market
            - Take into account:
                - Any information on condition
                - The materials the guitar is made of
                - Supplied accesories
                - Desirability of the specific model
                - Brand reputation
                - Year of manufacture
            - Include upper and lower value estimates for this market (in £s)
            - Include a brief explanation of your evaluation, consisting of no more than 250 characters.

        Use the high and low value estimates to define a range of possible values that reflects the confidence in your evaluation. The same value should not be repeated in both fields unless you are highly confident in your estimate!

        Th output should be a valid JSON object of the following format:

        {{
            "value_estimate_low": <lower end of value estimate range>,
            "value_estimate_high": <upper end of value estimate range>,
            "rationale": <explanation of value estimate> 
        }}

        RETURN ONLY A VALID JSON WITH THE SPECIFIED KEYS - THE RETURNED JSON OBJECT SHOULD BE PARSABLE USING THE json.loads METHOD."""

    valuation_data = call_llm_for_json(system, prompt, temperature=0.25)
    
    return valuation_data


def parse_lot_data(lot_data):
    # Initialize a dictionary for results.
    result = {}

    estimate = lot_data["estimate"]
    match = re.search(r"£(\d+)-(\d+)", estimate)
    if match:
        estimate_low = int(match.group(1))   # 3500
        result["estimate_low"] = estimate_low
        estimate_high = int(match.group(2))  # 5000
        result["estimate_high"] = estimate_high

    description = lot_data["description"]
    result["full_description"] = description

    body, *notes = description.split("*")

    if notes:
        result["notes"] = [note.strip() for note in notes if note.strip()]

    # Split the description on semicolons.
    parts = [part.strip() for part in body.split(";") if part.strip()]
    
    # The first part is the main description.
    if parts:
        summary = parts[0]
        # result["summary"] = summary
        # Optionally, use regex to extract the year if present.
        match = re.match(r"^(?P<year>\d{4})\s+(?P<title>.+)$", summary)
        if match:
            result["year"] = match.group("year")
            result["title"] = match.group("title")
        else:
            result["title"] = summary

        # Use the LLM to parse the title and merge response into results
        result = result | parse_title_with_llm(result["title"])

        # Look for a "made in" phrase in the summary.
        made_in_match = re.search(r"made in\s+([^,;]+)", summary, re.IGNORECASE)
        if made_in_match:
            result["made_in"] = made_in_match.group(1).strip()
    
    # Define the expected keys.
    keys = ["body", "neck", "fretboard", "frets", "electrics", "hardware", "case", "weight", "overall condition"]

    # Process each remaining part.
    for part in parts[1:]:
        # Look for the key: value pattern.
        if ":" in part:
            key, value = part.split(":", 1)
            key = key.strip().lower()  # normalize key to lowercase
            value = value.strip()
            if key == "weight":
                value = float(value.replace("kg", ""))
            # Only save if the key is one of our expected keys.
            if key in keys:
                result[key] = value
            else:
                # If key not found in expected list, add to notes.
                result.setdefault("notes", []).append(part)
        else:
            # If no colon, treat it as an additional note.
            result.setdefault("notes", []).append(part)
    
    return result


def save_data_to_disk(data, filename="scraped_data.jsonl"):
    """
    Saves the given data to a JSON Lines file on disk.
    Each record in the data list is written as a JSON object on a new line.
    
    Parameters:
      data: The data to save (e.g., a list of records).
      filename (str): The filename to write to.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            for record in data:
                json_line = json.dumps(record)
                f.write(json_line + "\n")
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Error saving data to disk: {e}")


def load_data_from_disk(filename="scraped_data.jsonl"):
    """
    Loads data from a JSON Lines file.

    Returns:
      A list of records (each record is a dictionary).
    """
    data = []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:  # Skip any empty lines
                    record = json.loads(line)
                    data.append(record)
        print(f"Data successfully loaded from {filename}")
    except Exception as e:
        print(f"Error loading data from disk: {e}")
    return data


def get_value_difference(entry):
    try:
        house_mean = (entry["estimate_low"] + entry["estimate_high"]) / 2
        llm_mean = (entry["value_estimate_low"] + entry["value_estimate_high"]) / 2
        return llm_mean - house_mean
    except KeyError:
        print(f"Missing data to calculate the value difference for {entry.get("title", "")}.")
        return None


def write_to_google_sheet(data, spreadsheet_name, worksheet_name, creds_file='credentials.json'):
    """
    Writes the scraped data to a Google Sheet in a single batch update.
    Expects data as a list of rows, where each row is a list of values.
    """
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open(spreadsheet_name).worksheet(worksheet_name)
    
    # Define the header fields you want to push.
    header_fields = [
        "Lot URL",
        "Type",
        "Title",
        "Brand",
        "Model",
        "Year",
        "Made In",
        "Weight (kg)",
        "Overall Condition",
        "House Estimated Price (low)",
        "House Estimated Price (high)",
        "LLM Estimated Price (low)",
        "LLM Estimated Price (high)",
        "LLM Valuation Rationale",
        "LLM vs House Difference",
        "Body",
        "Neck",
        "Fretboard", 
        "Frets",
        "Electrics",
        "Hardware",
        "Case", 
        "Notes",
        "Full Description"
    ]
    

    # Build the complete data: header followed by rows.
    all_rows = [header_fields]
    for lot_url, entry in data:
        row = [
            lot_url,
            entry.get("type", "").title(),
            entry.get("title", ""),
            entry.get("brand", ""),
            entry.get("model", ""),
            entry.get("year", ""),
            entry.get("made_in", ""),
            entry.get("weight", ""),
            entry.get("overall condition", ""),
            entry.get("estimate_low", ""),
            entry.get("estimate_high", ""),
            entry.get("value_estimate_low", ""),
            entry.get("value_estimate_high", ""),
            entry.get("rationale", ""),
            get_value_difference(entry),
            entry.get("body", ""),
            entry.get("neck", ""),
            entry.get("fretboard", ""),
            entry.get("frets", ""),
            entry.get("electrics", ""),
            entry.get("hardware", ""),
            entry.get("case", ""),
            "; ".join(entry.get("notes", [])) if entry.get("notes") else "",
            entry.get("full_description", "")
        ]
        all_rows.append(row)
    
    # Clear the sheet and write all rows in one batch.
    sheet.clear()
    sheet.update("A1", all_rows)


def main():
    base_url = "https://www.guitar-auctions.co.uk"
    preview_base_url = urljoin(base_url, "sale/234/the-guitar-auction---day-one---guitars-part-i-including-artist-associated-guitars-%26-memorabilia")

    page = 1
    all_lot_urls = []
    
    while True:
        # Construct the URL: first page without query parameter, subsequent pages with ?page=
        if page == 1:
            preview_url = preview_base_url
        else:
            preview_url = f"{preview_base_url}?page={page}"

        print(f"Fetching page {page}: {preview_url}")
        preview_html = fetch_page(preview_url)
        if not preview_html:
            print("Could not fetch the preview page.")
            return
        
        # Extract links to individual lot detail pages using the revised approach
        lot_urls = get_lot_links(preview_html, base_url)
        if not lot_urls:
            print(f"No lot links found on page {page}. Assuming this is the last page.")
            break
        
        print(f"Found {len(lot_urls)} lot(s).")
        all_lot_urls.extend(lot_urls)
        page += 1

    print(f"Total lot URLs found: {len(all_lot_urls)}")
    
    scraped_data = []
    
    # Process each lot: fetch detail page and parse the description and estimate.
    for idx, lot_url in enumerate(all_lot_urls, start=1):
        print(f"\nProcessing Lot {idx}: {lot_url}")
        lot_html = fetch_page(lot_url)
        if lot_html:
            lot_data = parse_lot_page(lot_html)
            print("Description:", lot_data["description"])
            print("Estimate:", lot_data["estimate"])
            parsed_lot_data = parse_lot_data(lot_data)
            llm_valuation = get_llm_valuation(lot_data["description"])
            try:
                parse_lot_data_and_valuation = parsed_lot_data | llm_valuation[0]
                scraped_data.append([lot_url, parse_lot_data_and_valuation])
            except Exception as e:
                print(f"Failed to merge parsed lot data and valuation: {e}")
        else:
            print("Failed to fetch the lot page.")
        # if idx >= 10:
        #     break

    save_data_to_disk(scraped_data)

    # Write the scraped data to a Google Sheet if any data was collected.
    if scraped_data:
        try:
            spreadsheet_name = "my-auction-lots"  # Replace with your actual spreadsheet name
            worksheet_name = "lots"              # Replace with your actual worksheet name
            write_to_google_sheet(scraped_data, spreadsheet_name, worksheet_name)
            print("Data written to Google Sheet.")
        except Exception as e:
            print(f"Failed to write data to Google Sheet: {e}")
    else:
        print("No data to write to Google Sheet.")
    
    langfuse.shutdown()

if __name__ == "__main__":
    main()
    