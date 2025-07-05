from nav_provider import NAVProvider
import requests
from bs4 import BeautifulSoup
from datetime import datetime


url = "https://fund.monex.co.jp/detail/"


class MonexProvider(NAVProvider):
    def get_latest_nav(self, fund):

        # Send a GET request to the page
        request_url = url + fund.codes['yahoo_finance']
        print (request_url)
        response = requests.get(request_url)
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        price_tag = soup.find('span', class_="price")
        last_price = float(price_tag.get_text(strip=True).replace(',', ''))
        
        last_date = soup.find('span', class_="basis-date")
        #format is "基準日：2025年07月04日"
        if last_date:
            last_date = last_date.get_text(strip=True)
            last_date = last_date.split('：')[1]  # Split to remove "基準日："
            last_date = datetime.strptime(last_date, "%Y年%m月0%d日")

        #returns (date, price)
        return (last_date, last_price)


if __name__ == "__main__":
    # Example usage
    provider = MonexProvider()
    fund = type('Fund', (object,), {'codes': {'yahoo_finance': '10311144'}})  # Mock fund object
    nav = provider.get_latest_nav(fund)
    print(f"The latest NAV for the fund is: {nav}")