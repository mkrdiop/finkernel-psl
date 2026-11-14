from enum import Enum

class Currency(str, Enum):
    EUR = "EUR"
    USD = "USD"
    JPY = "JPY"
    GBP = "GBP"
    CHF = "CHF"

class FinancialType(str, Enum):
    MONEY = "Money"
    CURRENCY = "Currency"
    RATE = "Rate"
    PERCENTAGE = "Percentage"
    PRICE = "Price"
    VOLATILITY = "Volatility"
    PROBABILITY = "Probability"
    QUANTITY = "Quantity"
    RATIO = "Ratio"
    INDEX_LEVEL = "IndexLevel"
    FREQUENCY = "Frequency"
    DATE = "Date"
    DURATION = "Duration"
