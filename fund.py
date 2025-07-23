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


    def get_fund_nav(self):
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()

        cur.execute("SELECT AtDate, NAV FROM FUND_NAV WHERE FundID = ? ORDER BY AtDate DESC", (self.fund_id,))
        rows = cur.fetchall()

        conn.close()

        if rows is not None:
            for row in rows:
                self.nav[row[0]] = float(row[1])
