import datetime
import sqlite3
from config import conf
from enum import Enum


class TransactionType(Enum):
    BUY = "お買付"
    SELL = "解約"
    DIVIDEND_REINVEST = "再投資買付"
    DIVIDEND_RECEIVED = "分配金"
    OTHER = "OTHER"

    
    def to_emoji(self)-> str:
        match self:
            case TransactionType.BUY:
                return "💸"
            case TransactionType.SELL:
                return "💰"
            case TransactionType.DIVIDEND_REINVEST:
                return "♻️"
            case TransactionType.DIVIDEND_RECEIVED:
                return "🪙"
            case TransactionType.OTHER:
                return "❓"

    def to_short(self) -> str:
        match self:
            case TransactionType.BUY:
                return "Buy"
            case TransactionType.SELL:
                return "Sell"
            case TransactionType.DIVIDEND_REINVEST:
                return "Div Reinvest"
            case TransactionType.DIVIDEND_RECEIVED:
                return "Div Received"
            case TransactionType.OTHER:
                return "Other"

class Fund:
    def __init__(self, fund_id, name, currency):
        self.fund_id = fund_id
        self.name = name
        self.currency = currency
        self.codes = {}
        self.nav = {}
        self.dividends = None
        self.transactions = []


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

        cur.execute("SELECT AtDate, Amount, AccountingPeriod FROM DIVIDEND WHERE FundID = ? ORDER BY AtDate DESC", (self.fund_id,))
        rows = cur.fetchall()

        conn.close()

        self.dividends = []  # Reset dividends list
        if rows is not None:
            for row in rows:
                #dividends are (date, amount, accounting_period (if present))
                self.dividends.append(dict(date=datetime.datetime.strptime(row[0][:10], "%Y-%m-%d").date(), amount=float(row[1]), accounting_period=int(row[2]) if row[2] is not None and row[2] != "" else 0))


    def get_dividends_between_dates(self, start_date, end_date):
        """
        Get the fund's dividends between two dates.
        """
        if not self.dividends:
            self.get_dividends()

        res = []
        for d in self.dividends:
            if start_date <= d['date'] and (end_date is None or d['date'] <= end_date):
                res.append(d)
        return res


    def get_transactions(self):
        x = Fund.get_all_transactions(self.fund_id)
        if x is not None:
            self.transactions = x


    @classmethod
    def get_all_transactions(cls, fund_id: int = None):
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()

        cur.execute("""
    SELECT 
                    X.*, 
                    F.Name as FundName,
                    LASTNAV.NAV as LastNAV,
                    (X.Unit * LASTNAV.NAV / 10000) - X.XactPrice as LastNavPnL
    FROM 
                    XACT as X 
                    JOIN FUND as F ON X.FundID = F.FundID

                    JOIN (
                    SELECT N.FundId, N.AtDate, N.NAV as NAV
                    from FUND_NAV as N
                    WHERE
                    1=1
                    GROUP BY N.FundId having N.AtDate = Max(N.AtDate)
                    ) as LASTNAV ON F.FundId = LASTNAV.FundId

    WHERE 1=1
    AND (X.FundID = ? OR ? IS NULL)
    ORDER BY TradeDate DESC""",
    (fund_id if fund_id else None, fund_id if fund_id else None))

        rows = cur.fetchall()
        transactions = []
        
        for row in rows:
            transactions.append({
                'trade_date': row[1],
                'exec_date': row[2],
                'type': row[3],
                'xtype': TransactionType(row[3]),
                'fundid': row[4],
                'unit': row[5],
                'unit_price': row[6],
                'amount': row[7],
                'currency': row[8],
                'fundname': row[9],
                'last_nav': row[10],
                'last_nav_pnl': row[11],
            })

        conn.close()
        return transactions



    @property
    def stats(self) -> dict:
        """
        Get the statistics panel data.
        """
        today = datetime.date.today()
        start_of_year = datetime.datetime(today.year, 1, 1).date()
        start_of_last_year = datetime.datetime(today.year - 1, 1, 1).date()
        one_year_ago = today.replace(year=today.year - 1)
        three_years_ago = today.replace(year=today.year - 3)

        
        return {
            "latest_nav": self.latest_nav,
            "nav_diff": self.nav_diff,

            "return_ytd": self.stats_nav_return(start_of_year, None, include_dividends=True),
            "return_1y": self.stats_nav_return(one_year_ago, None, include_dividends=True),
            "return_3y": self.stats_nav_return(three_years_ago, None, include_dividends=True),
            "return_last_year": self.stats_nav_return(start_of_last_year, start_of_year, include_dividends=True),

            "cagr_ytd": self.stats_cagr(self.get_fund_nav_at_date(start_of_year), self.latest_nav, 1),
            "cagr_1y": self.stats_cagr(self.get_fund_nav_at_date(one_year_ago), self.latest_nav, 1),
            "cagr_3y": self.stats_cagr(self.get_fund_nav_at_date(three_years_ago), self.latest_nav, 3),
            "cagr_last_year": self.stats_cagr(self.get_fund_nav_at_date(start_of_last_year), self.get_fund_nav_at_date(start_of_year), 1),

            "excess_return_ytd": self.stats_nav_return(start_of_year, None, conf.risk_free_rate  * float(today.timetuple().tm_yday) / 365.0, include_dividends=True),
            "excess_return_1y": self.stats_nav_return(one_year_ago, None, conf.risk_free_rate, include_dividends=True),
            "excess_return_3y": self.stats_nav_return(three_years_ago, None, conf.risk_free_rate * 3, include_dividends=True),

        }


    def stats_nav_return(self, initial_date, final_date, risk_free_rate=0.0, include_dividends=False):
        """
        Calculate the return percentage based on initial and final NAV.
        """
        initial_nav = self.get_fund_nav_at_date(initial_date)
        final_nav = None
        if final_date is None:
            final_nav = self.latest_nav
        else:
            final_nav = self.get_fund_nav_at_date(final_date)

        if include_dividends:
            dividends = self.get_dividends_between_dates(initial_date, final_date)
            sum_divs = sum([d['amount'] for d in dividends])
            #print (f"Sum divs = {sum_divs} for period {initial_date} to {final_date}")
            final_nav += sum_divs

        if initial_nav == 0 or not initial_nav:
            return 0.0
        return ((final_nav - initial_nav) / initial_nav - risk_free_rate) * 100.0
    

    def stats_cagr(self, initial_nav, final_nav, years):
        """
        Calculate the Compound Annual Growth Rate (CAGR).
        """
        if years <= 0 or initial_nav == 0 or not initial_nav:
            return 0.0
        return ((final_nav / initial_nav) ** (1 / years) - 1) * 100.0
    

    @classmethod
    def delete_fund(cls, fund_id: int) -> bool:
        """
        Deletes a fund and all its associated data from the database.
        """
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()
        try:
            # Delete associated FUND_CODE entries
            cur.execute("DELETE FROM FUND_CODE WHERE FundID = ?", (fund_id,))
            # Delete associated FUND_NAV entries
            cur.execute("DELETE FROM FUND_NAV WHERE FundID = ?", (fund_id,))
            # Delete associated DIVIDEND entries
            cur.execute("DELETE FROM DIVIDEND WHERE FundID = ?", (fund_id,))
            # Delete associated XACT entries
            cur.execute("DELETE FROM XACT WHERE FundID = ?", (fund_id,))
            # Finally, delete the fund itself
            cur.execute("DELETE FROM FUND WHERE FundID = ?", (fund_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting fund {fund_id}: {e}")
            return False
        finally:
            conn.close()