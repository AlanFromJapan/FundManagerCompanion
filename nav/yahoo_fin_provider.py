from nav.nav_provider import NAVProvider
import requests
from bs4 import BeautifulSoup
from datetime import datetime


url_latest = "https://finance.yahoo.co.jp/quote/"
url_history = "https://finance.yahoo.co.jp/quote/{?}/history"


class YahooFinProvider(NAVProvider):
    def get_latest_nav(self, fund):
        request_url = url_latest + fund.codes['yahoo_finance']
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



    def get_history_nav(self, fund):
        request_url = url_history.replace("{?}", fund.codes['yahoo_finance'])
        
        nav_dict = {}
        try:
            # Send a GET request to the page
            page_content = NAVProvider.get_page(request_url)

            # Parse the HTML content
            soup = BeautifulSoup(page_content, 'html.parser')

            #find the table of class table__2wv6
            table = soup.find('table', class_='table__26JH')
            if table:
                tbody = table.find('tbody')
                rows = tbody.find_all('tr')
                rows = rows[1:]  # Skip the header row
                if len(rows) > 1:
                    # Get the last row (most recent date)
                    for row in rows:                        
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            # Extract date and price
                            date_str = cells[0].get_text(strip=True)
                            price_str = cells[1].find("span").get_text(strip=True).replace(',', '')
                            last_date = datetime.strptime(date_str, "%Y年%m月%d日")
                            last_price = float(price_str)
                            nav_dict[last_date] = last_price

        except Exception as e:
            print(f"Error fetching NAV for {fund.codes['yahoo_finance']} at URL [{request_url}]: {e}")
        
        #second value is None since we don't return the dividends
        return nav_dict, None
        

if __name__ == "__main__":
    # Example usage
    provider = YahooFinProvider()
    fund = type('Fund', (object,), {'codes': {'yahoo_finance': '03311112'}})  # Mock fund object
    nav = provider.get_latest_nav(fund)
    print(f"The latest NAV for the fund is: {nav}")

    print("=" * 20)
    print("Fetching historical NAVs...")
    history_nav = provider.get_history_nav(fund)
    for date, price in history_nav.items():
        print(f"Date: {date.strftime('%Y-%m-%d')}, NAV: {price}")
    print("=" * 20)
    print("Done fetching historical NAVs.")