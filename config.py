import datetime
import sqlite3

class Config(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__risk_free_rate = None 


    @property
    def risk_free_rate(self):
        #cache the risk-free rate to avoid multiple DB calls
        if self.__risk_free_rate is not None:
            return self.__risk_free_rate
        
        conn = sqlite3.connect(self['DB_PATH'])
        cur = conn.cursor()
        cur.execute("SELECT Value FROM CONFIG WHERE Key = 'RiskFreeRate'")
        row = cur.fetchone()
        conn.close()
        if row is not None:
            self.__risk_free_rate = float(row[0])
        else:
            print("Risk-free rate not found in the database, returning default value of", self.__risk_free_rate)
            # Default risk-free rate if not found in DB
            self.__risk_free_rate = 0.0305 # Default risk-free rate as of Aug 2025

        return self.__risk_free_rate


    @risk_free_rate.setter
    def risk_free_rate(self, value):
        value = float(value)
        if value <= 0:
            raise ValueError("Risk-free rate must be a positive number.")
        
        conn = sqlite3.connect(self['DB_PATH'])
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO CONFIG (Key, Value, LastUpdate) VALUES ('RiskFreeRate', ?, ?)", (value, datetime.datetime.now()  ))
        conn.commit()
        conn.close()
        print("Risk-free rate set to", value)
        self.__risk_free_rate = value

# Usage
conf = Config(DB_PATH='data/data.db', SECRET_KEY='your_secret_key_here')

