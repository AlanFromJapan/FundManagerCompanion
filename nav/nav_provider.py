from abc import ABC, abstractmethod
from threading import Lock
import requests

class NAVProvider(ABC):
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @abstractmethod
    def get_latest_nav(self, fund):
        """
        Return a tuple (price, date) for the latest known NAV of the given fund.
        """
        pass

    @abstractmethod
    def get_history_nav(self, fund) -> dict:
        """
        Return a dictionary with dates as keys and NAVs as values for the given fund.
        """
        pass

    @staticmethod
    def get_page(url):
        response = requests.get(url, timeout=3)
        response.raise_for_status()
        return response.text
