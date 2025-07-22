from nav.nav_provider import NAVProvider
import requests
from bs4 import BeautifulSoup
from datetime import datetime


url = "https://finance.yahoo.co.jp/quote/"


class YahooFinProvider(NAVProvider):
    def get_latest_nav(self, fund):
        request_url = url + fund.codes['yahoo_finance']
        try:
            # Send a GET request to the page
            page_content = NAVProvider.get_page(request_url)

            # Parse the HTML content
            soup = BeautifulSoup(page_content, 'html.parser')

            # Find the <p> tag with class="price__1VJb"
            price_tag = soup.find('span', class_="StyledNumber__value__3rXW")
            last_price = float(price_tag.get_text(strip=True).replace(',', ''))
            
            last_date = soup.find('time')
            #format is "MM/DD"
            if last_date:
                current_year = datetime.now().year
                last_date = last_date.get_text(strip=True)
                last_date = f"{current_year }/{last_date}" #YYYY/MM/DD
                last_date = datetime.strptime(last_date, "%Y/%m/%d")

            #returns (date, price)
            return (last_date, last_price)
        except Exception as e:
            print(f"Error fetching NAV for {fund.codes['yahoo_finance']} at URL [{request_url}]: {e}")
            return (None, None)


if __name__ == "__main__":
    # Example usage
    provider = YahooFinProvider()
    fund = type('Fund', (object,), {'codes': {'yahoo_finance': '03311112'}})  # Mock fund object
    nav = provider.get_latest_nav(fund)
    print(f"The latest NAV for the fund is: {nav}")