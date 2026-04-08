import csv
import io
from nav.nav_provider import NAVProvider
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import unittest

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
            response_raw = response.content
            response_decoded = response_raw.decode('shift_jis')
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



class TestToshinkyokaiProvider(unittest.TestCase):
    def setUp(self):
        self.provider = toshinkyokai_provider()

    def test_get_history_nav(self):
        # This test assumes that the fund with ISIN "JP90C0003106" and toushinkyokai code "47311007" exists and has data
        class MockFund:
            def __init__(self):
                self.codes = {
                    "ISIN": "JP90C0003106",
                    "toushinkyokai": "47311007"
                }
                self.fund_id = "mock_fund_id"
                self.name = "Mock Fund"

        fund = MockFund()
        nav_dict, div_dict = self.provider.get_history_nav(fund)

        # Check if NAV dictionary is not empty
        self.assertTrue(len(nav_dict) > 0, "NAV dictionary should not be empty")
        # Check if dividend dictionary is not empty
        self.assertTrue(len(div_dict) > 0, "Dividend dictionary should not be empty")
        # Check if the keys in NAV dictionary are datetime objects
        for key in nav_dict.keys():
            self.assertIsInstance(key, datetime, "Keys in NAV dictionary should be datetime objects")
        # Check if the values in NAV dictionary are integers
        for value in nav_dict.values():
            self.assertIsInstance(value, int, "Values in NAV dictionary should be integers")