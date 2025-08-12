import datetime
import sqlite3
from config import conf


class Fund:
    def __init__(self, fund_id, name, currency):
        self.fund_id = fund_id
        self.name = name
        self.currency = currency
        self.codes = {}
        self.nav = {}
        self.dividends = {}

    @classmethod
    def from_db_row(cls, row):
        # Assumes row is (FundID, Name, Currency)
        return cls(row[0], row[1], row[2])




    def __repr__(self):
        return f"<Fund id={self.fund_id} name={self.name} currency={self.currency}>"

    @property
    def nav_sorted(self):
        """
        Returns a list of (date, nav) tuples sorted by date descending.
        """
        return sorted(((x[0], x[1]) for x in self.nav.items()), key=lambda x: x[0], reverse=True)


    @property
    def latest_nav(self):
        """
        Returns the latest NAV value.
        """
        if not self.nav:
            return None
        return self.nav_sorted[0][1] if self.nav_sorted else None

    @property
    def nav_diff(self):
        """
        Returns the difference between the latest NAV and the previous one for all nav in percentage and amount.
        """
        if len(self.nav_sorted) < 2:
            return None
        diffs = []
        snav = self.nav_sorted
        for i in range(1, len(snav)):
            date, nav = snav[i]
            _, prev_nav = snav[i - 1]
            diffp = -(nav - prev_nav) / prev_nav * 100 if prev_nav != 0 else 0
            diffa = -(nav - prev_nav)
            diffs.append({'date': date, 'diffpct': diffp, 'diffamt': diffa})

        return diffs
    

    def get_fund_nav(self, limit=100):
        """
        Get the fund's NAV history in DESCENDING order (latest first).
        """
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()

        cur.execute("SELECT AtDate, NAV FROM FUND_NAV WHERE FundID = ? ORDER BY AtDate DESC LIMIT ?", (self.fund_id, limit))
        rows = cur.fetchall()

        conn.close()

        if rows is not None:
            for row in rows:
                self.nav[row[0]] = float(row[1])


    def get_fund_nav_at_date(self, at_date):
        """
        Get the NAV for the fund at a specific date or immediately after.
        """
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()

        cur.execute("SELECT NAV FROM FUND_NAV WHERE FundID = ? AND AtDate >= ? ORDER BY AtDate ASC LIMIT 1", (self.fund_id, at_date))
        row = cur.fetchone()

        conn.close()

        if row is not None:
            return float(row[0])
        return None



    def get_dividends(self):
        """
        Get the fund's dividends history in DESCENDING order of accounting period (latest first).
        """
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()

        cur.execute("SELECT AtDate, Amount, AccountingPeriod FROM DIVIDEND WHERE FundID = ? ORDER BY AccountingPeriod DESC", (self.fund_id,))
        rows = cur.fetchall()

        conn.close()

        if rows is not None:
            for row in rows:
                self.dividends[int(row[2]) if row[2] is not None and row[2] != "" else 0] = (float(row[1]), row[0])


    @property
    def stats(self) -> dict:
        return self.stats_get_panel()

    def stats_get_panel(self) -> dict:
        """
        Get the statistics panel data.
        """
        today = datetime.date.today()
        start_of_year = datetime.datetime(today.year, 1, 1)
        start_of_last_year = datetime.datetime(today.year - 1, 1, 1)
        one_year_ago = today.replace(year=today.year - 1)
        three_years_ago = today.replace(year=today.year - 3)

        
        return {
            "latest_nav": self.latest_nav,
            "nav_diff": self.nav_diff,
            
            "return_ytd": self.stats_nav_return(self.get_fund_nav_at_date(start_of_year), self.latest_nav),
            "return_1y": self.stats_nav_return(self.get_fund_nav_at_date(one_year_ago), self.latest_nav),
            "return_3y": self.stats_nav_return(self.get_fund_nav_at_date(three_years_ago), self.latest_nav),
            "return_last_year": self.stats_nav_return(self.get_fund_nav_at_date(start_of_last_year), self.get_fund_nav_at_date(start_of_year)),

            "cagr_ytd": self.stats_cagr(self.get_fund_nav_at_date(start_of_year), self.latest_nav, 1),
            "cagr_1y": self.stats_cagr(self.get_fund_nav_at_date(one_year_ago), self.latest_nav, 1),
            "cagr_3y": self.stats_cagr(self.get_fund_nav_at_date(three_years_ago), self.latest_nav, 3),
            "cagr_last_year": self.stats_cagr(self.get_fund_nav_at_date(start_of_last_year), self.get_fund_nav_at_date(start_of_year), 1)

        }


    def stats_nav_return(self, initial_nav, final_nav):
        """
        Calculate the return percentage based on initial and final NAV.
        """
        if initial_nav == 0 or not initial_nav:
            return 0.0
        return (final_nav - initial_nav) / initial_nav * 100.0
    

    def stats_cagr(self, initial_nav, final_nav, years):
        """
        Calculate the Compound Annual Growth Rate (CAGR).
        """
        if years <= 0 or initial_nav == 0 or not initial_nav:
            return 0.0
        return ((final_nav / initial_nav) ** (1 / years) - 1) * 100.0