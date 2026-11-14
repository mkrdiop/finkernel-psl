from typing import List, Dict, Any
from datetime import datetime, timedelta

class EventScheduler:
    @staticmethod
    def generate_observation_dates(inception_date: str, maturity_date: str, frequency: str) -> List[str]:
        start = datetime.strptime(inception_date, "%Y-%m-%d")
        end = datetime.strptime(maturity_date, "%Y-%m-%d")
        
        months_step = 3 if frequency.lower() == "quarterly" else (6 if frequency.lower() == "semiannual" else 12)
        dates = []
        current = start + timedelta(days=int(30.4375 * months_step))
        
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current = current + timedelta(days=int(30.4375 * months_step))
            
        return dates
