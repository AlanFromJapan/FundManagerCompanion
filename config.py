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
        
        # Default risk-free rate as of Aug 2025 is 0.005 (0.5%)
        self.__risk_free_rate = float(self.get_DB_value('RiskFreeRate', default=0.005))

        return self.__risk_free_rate


    @risk_free_rate.setter
    def risk_free_rate(self, value):
        value = float(value)
        if value <= 0:
            raise ValueError("Risk-free rate must be a positive number.")

        self.set_DB_value('RiskFreeRate', value)
        self.__risk_free_rate = value


    @property
    def target_yearly_rate(self):
        #cache the target yearly rate to avoid multiple DB calls
        if self.__target_yearly_rate is not None:
            return self.__target_yearly_rate

        # Default target yearly rate is 0.03 (3%)
        self.__target_yearly_rate = float(self.get_DB_value('TargetYearlyRate', default=0.03))

        return self.__target_yearly_rate
    
    
    @target_yearly_rate.setter
    def target_yearly_rate(self, value):
        value = float(value)
        if value <= 0:
            raise ValueError("Target yearly rate must be a positive number.")

        self.set_DB_value('TargetYearlyRate', value)
        self.__target_yearly_rate = value


    def get_DB_value(self, key, default=None):
        conn = sqlite3.connect(self['DB_PATH'])
        cur = conn.cursor()
        cur.execute("SELECT Value FROM CONFIG WHERE Key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        if row is not None:
            return row[0]
        return default
    

    def set_DB_value(self, key, value):
        conn = sqlite3.connect(self['DB_PATH'])
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO CONFIG (Key, Value, LastUpdate) VALUES (?, ?, ?)", (key, value, datetime.datetime.now() ))
        conn.commit()
        conn.close()
        print(f"{key} set to", value)


# Usage
conf = Config(DB_PATH='data/data.db', SECRET_KEY='your_secret_key_here')

