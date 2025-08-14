import csv
import io
from nav.nav_provider import NAVProvider
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class toshinkyokai_provider(NAVProvider):
    def __init__(self):
        super().__init__()


    def get_latest_nav(self, fund):
        #Could do it later but an overkill...
        raise NotImplementedError("This provider does not implement get_latest_nav. ")


    def get_history_nav(self, fund):
        try:
            URL_ITA = "https://toushin-lib.fwg.ne.jp/FdsWeb/FDST030000/csv-file-download?isinCd={isin}&associFundCd={id}"
            # Placeholder for actual implementation
            # This should include fetching data from the IITA and updating the fund's NAV
            url = URL_ITA.format(isin=fund.codes["ISIN"], id=fund.codes["yahoo_finance"] if fund.codes.get("toushinkyokai") is None else fund.codes.get("toushinkyokai"))
            print(f"Fetching NAV from URL: {url}")

            nav_dict = {}
            div_dict = {}

            response = requests.get(url)
            response.raise_for_status()
            response_raw = response.text
            response_decoded = response_raw.encode('utf-8').decode('utf-8-sig')  # Handle BOM if present
            csv_data = io.StringIO(response_decoded)
            # Now csv_data can be used to read the CSV content in memory
            reader = csv.reader(csv_data, delimiter=',')
            cnt = 0
            for row in reader:
                if cnt == 0:
                    # Skip header row
                    cnt += 1
                    continue
                cnt += 1
                nav_date = datetime.strptime(row[0].strip(), "%Y年%m月%d日")
                nav = int(row[1].strip())
                _ = int(row[2].strip()) if len(row) > 2 else None #AUM
                dividend = row[3].strip() if len(row) > 3 else None
                accounting_period = row[4].strip() if len(row) > 4 else None

                nav_dict[nav_date] = nav
                if dividend is not None and accounting_period is not None and dividend != "":
                    div_dict[nav_date] = (dividend, accounting_period)
            print(f"Total rows processed: {cnt}")

            return nav_dict, div_dict
        except Exception as e:
            print(f"Error importing whole NAV for fund {fund.fund_id} ({fund.name}): {e}")
