import requests
from bs4 import BeautifulSoup

# URL of the fund page
url = "https://finance.yahoo.co.jp/quote/"

def get_NAV(associated_fund_code):
    
    # Send a GET request to the page
    response = requests.get(url + associated_fund_code)
    response.raise_for_status()

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the <p> tag with class="price__1VJb"
    price_tag = soup.find('p', class_="price__1VJb")

    return price_tag.get_text(strip=True)

if __name__ == "__main__":
    # Example usage
    codes = ["03311112", "0131106B"] 

    for code in codes:
        fund_code = code
        print(f"Fetching NAV for fund code: {fund_code}")
        nav = get_NAV(fund_code)
        print(f"The NAV for the fund with code {fund_code} is: {nav}")
        print ("-" * 40)