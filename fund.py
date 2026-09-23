import datetime
import sqlite3
from config import conf
from enum import Enum
import math
from cachetools import cached, TTLCache

cache = TTLCache(maxsize=500, ttl=10)

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
    def __init__(self, fund_id, name, currency, latest_units=0):
        self.fund_id = fund_id
        self.name = name
        self.currency = currency
        self.codes = {}
        self.nav = {}
        self.dividends = None
        self.transactions = []
        self.latest_units = latest_units


    @classmethod
    def from_db_row(cls, row):
        # Assumes row is (FundID, Name, Currency, LatestUnits)
        return cls(row[0], row[1], row[2], row[3])




    def __repr__(self):
        return f"<Fund id={self.fund_id} name={self.name} currency={self.currency} latest_units={self.latest_units}>"

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
    @cached(cache)
    def stats(self) -> dict:
        """
        Get the statistics panel data.
        """
        today = datetime.date.today()
        start_of_year = datetime.datetime(today.year, 1, 1).date()
        start_of_last_year = datetime.datetime(today.year - 1, 1, 1).date()
        one_year_ago = today.replace(year=today.year - 1)
        three_years_ago = today.replace(year=today.year - 3)

        
        stats = {
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

            "invested_amount": self.stats_invested_amount(),
            "total_units": self.stats_total_units(),
            "current_value": (self.stats_total_units() * self.latest_nav / 10000) if self.latest_nav else 0.0,
            "unrealized_pnl": ((self.stats_total_units() * self.latest_nav / 10000) - self.stats_invested_amount()) if self.latest_nav else 0.0,
        }

        #add more stats as needed, like volatility
        vol_stats = self.calculate_volatility(days_back=365, annualized=True)
        if vol_stats is not None:
            #merge both dict into stats
            stats = {**stats, **vol_stats}

        #regressions
        trend_stats = self.calculate_advanced_nav_trend(days_back=365)
        if trend_stats is not None:
            stats = {**stats, **trend_stats}

        return stats
    

    def stats_total_units(self):
        """
        Calculate the total units held based on transactions.
        """
        total_units = 0.0
        for x in self.transactions:
            if x['xtype'] in {TransactionType.BUY, TransactionType.DIVIDEND_REINVEST}:
                total_units += x['unit']
            elif x['xtype'] == TransactionType.SELL:
                total_units -= x['unit']
        return total_units
    

    def stats_invested_amount(self):
        """
        Calculate the total invested amount based on transactions.
        """
        total_invested = 0.0
        for x in self.transactions:
            if x['xtype'] in {TransactionType.BUY, TransactionType.DIVIDEND_REINVEST}:
                total_invested += x['amount']
            elif x['xtype'] == TransactionType.SELL:
                total_invested -= x['amount']
        return total_invested
    

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

        if include_dividends and final_nav is not None:
            dividends = self.get_dividends_between_dates(initial_date, final_date)
            sum_divs = sum([d['amount'] for d in dividends])
            #print (f"Sum divs = {sum_divs} for period {initial_date} to {final_date}")
            final_nav += sum_divs if sum_divs is not None else 0

        if initial_nav == 0 or not initial_nav:
            return 0.0
        
        try:
            return ((final_nav - initial_nav) / initial_nav - risk_free_rate) * 100.0
        except Exception as e:
            print(f"Error calculating NAV return in stats_nav_return() for fund {self.name} (ID={self.fund_id}): {e}")
            return -99999.0
    

    def stats_cagr(self, initial_nav, final_nav, years):
        """
        Calculate the Compound Annual Growth Rate (CAGR).
        """
        if years <= 0 or initial_nav == 0 or not initial_nav:
            return 0.0
        try:
            return ((final_nav / initial_nav) ** (1 / years) - 1) * 100.0
        except Exception as e:
            print(f"Error calculating CAGR in stats_cagr() for fund {self.name} (ID={self.fund_id}): {e}")
            return -99999.0
    

    @classmethod
    def delete_fund(cls, fund_id: int) -> bool:
        """
        Deletes a fund and all its associated data from the database.
        """
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()
        try:

            # Forbidd myself to corrupt the database by deleting a fund that still has transactions
            cur.execute("SELECT * FROM XACT WHERE FundID = ? LIMIT 1", (fund_id,))
            if cur.fetchone() is not None:
                print(f"Cannot delete fund {fund_id} because it still has transactions.")
                return False

            # Looks ok to delete...
            # Delete associated FUND_CODE entries
            cur.execute("DELETE FROM FUND_CODE WHERE FundID = ?", (fund_id,))
            # Delete associated FUND_NAV entries
            cur.execute("DELETE FROM FUND_NAV WHERE FundID = ?", (fund_id,))
            # Delete associated DIVIDEND entries
            cur.execute("DELETE FROM DIVIDEND WHERE FundID = ?", (fund_id,))

            # Finally, delete the fund itself
            cur.execute("DELETE FROM FUND WHERE FundID = ?", (fund_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting fund {fund_id}: {e}")
            return False
        finally:
            conn.close()


    @cached(cache)
    def calculate_volatility(self, days_back=365, annualized=True) -> dict:
        """
        Calculate the volatility (standard deviation of returns) over a specified period.
        
        Args:
            days_back: Number of days to look back (default 365 for 1 year)
            annualized: If True, annualize the volatility (multiply by sqrt(252))
        
        Returns:
            Dict with volatility metrics
        """

        
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()
        
        # Get NAV data for the specified period
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        cur.execute("""
            SELECT AtDate, NAV 
            FROM FUND_NAV 
            WHERE FundID = ? AND AtDate >= ? 
            ORDER BY AtDate ASC
        """, (self.fund_id, start_date))
        
        rows = cur.fetchall()
        conn.close()
        
        if len(rows) < 2:
            return None
        
        # Calculate daily returns (percentage change)
        daily_returns = []
        nav_values = [float(row[1]) for row in rows]
        
        for i in range(1, len(nav_values)):
            daily_return = (nav_values[i] - nav_values[i-1]) / nav_values[i-1] * 100
            daily_returns.append(daily_return)
        
        if not daily_returns:
            return None
        
        # Calculate mean return
        mean_return = sum(daily_returns) / len(daily_returns)
        
        # Calculate variance
        variance = sum((return_val - mean_return) ** 2 for return_val in daily_returns) / len(daily_returns)
        
        # Calculate standard deviation (volatility)
        volatility = math.sqrt(variance)
        
        # Annualize if requested (multiply by sqrt of trading days per year)
        if annualized:
            annualized_volatility = volatility * math.sqrt(252)  # 252 trading days per year
        else:
            annualized_volatility = volatility
        
        return {
            'daily_volatility': volatility,
            'annualized_volatility': annualized_volatility if annualized else None,
            'mean_daily_return': mean_return,
            'data_points': len(daily_returns),
            'period_days': days_back,
            'volatility_category': self._classify_volatility(annualized_volatility if annualized else volatility)
        }

    def _classify_volatility(self, volatility):
        """Classify volatility level for easy interpretation."""
        if volatility < 5:
            return 'very_low'
        elif volatility < 10:
            return 'low'
        elif volatility < 15:
            return 'moderate'
        elif volatility < 25:
            return 'high'
        else:
            return 'very_high'
        

    @cached(cache)
    def calculate_advanced_nav_trend(self, days_back=365) -> dict:
        """
        Advanced trend analysis using polynomial regression and additional metrics.
        """
        import numpy as np
        from scipy import stats
        from sklearn.preprocessing import PolynomialFeatures
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score
        
        # Get NAV data (same database query as above)
        conn = sqlite3.connect(conf['DB_PATH'])
        cur = conn.cursor()
        
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        cur.execute("""
            SELECT AtDate, NAV 
            FROM FUND_NAV 
            WHERE FundID = ? AND AtDate >= ? 
            ORDER BY AtDate ASC
        """, (self.fund_id, start_date))
        
        rows = cur.fetchall()
        conn.close()
        
        if len(rows) < 10:  # Need more data for advanced analysis
            return None
        
        # Prepare data
        dates = [datetime.datetime.strptime(row[0], '%Y-%m-%d') for row in rows]
        navs = np.array([float(row[1]) for row in rows])
        x_days = np.array([(d - dates[0]).days for d in dates]).reshape(-1, 1)
        
        # Linear regression
        linear_reg = LinearRegression()
        linear_reg.fit(x_days, navs)
        linear_predictions = linear_reg.predict(x_days)
        linear_r2 = r2_score(navs, linear_predictions)
        
        # Polynomial regression (degree 2)
        poly_features = PolynomialFeatures(degree=2)
        x_poly = poly_features.fit_transform(x_days)
        poly_reg = LinearRegression()
        poly_reg.fit(x_poly, navs)
        poly_predictions = poly_reg.predict(x_poly)
        poly_r2 = r2_score(navs, poly_predictions)
        
        # Statistical tests
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_days.flatten(), navs)
        
        # Volatility analysis
        daily_returns = np.diff(navs) / navs[:-1] * 100
        volatility = np.std(daily_returns) * np.sqrt(252)  # Annualized volatility
        
        return {
            'linear_slope': slope,
            'linear_r_squared': linear_r2,
            'polynomial_r_squared': poly_r2,
            'p_value': p_value,
            'volatility': volatility,
            'annual_trend_pct': (slope * 365 / navs[0]) * 100,
            'trend_significance': 'significant' if p_value < 0.05 else 'not_significant',
            'best_fit': 'polynomial' if poly_r2 > linear_r2 + 0.05 else 'linear',
            'trend_strength': self._classify_trend_strength(poly_r2)
        }

    def _classify_trend_strength(self, r_squared):
        """Classify trend strength based on R-squared value."""
        if r_squared >= 0.8:
            return 'very_strong'
        elif r_squared >= 0.6:
            return 'strong'
        elif r_squared >= 0.4:
            return 'moderate'
        elif r_squared >= 0.2:
            return 'weak'
        else:
            return 'very_weak'
    