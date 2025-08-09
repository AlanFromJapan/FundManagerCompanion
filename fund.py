import sqlite3
from config import conf


class Fund:
    def __init__(self, fund_id, name, currency):
        self.fund_id = fund_id
        self.name = name
        self.currency = currency
        self.codes = {}
        self.nav = {}

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
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()

        cur.execute("SELECT AtDate, NAV FROM FUND_NAV WHERE FundID = ? ORDER BY AtDate DESC LIMIT ?", (self.fund_id, limit))
        rows = cur.fetchall()

        conn.close()

        if rows is not None:
            for row in rows:
                self.nav[row[0]] = float(row[1])
