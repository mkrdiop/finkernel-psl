import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


class OptionEngine:
    @staticmethod
    def black_scholes(S, K, T, r, q, sigma, option_type="call"):
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type.lower() == "call":
            price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            delta = np.exp(-q * T) * norm.cdf(d1)
            theta = (
                -(S * sigma * np.exp(-q * T) * norm.pdf(d1)) / (2 * np.sqrt(T))
                - r * K * np.exp(-r * T) * norm.cdf(d2)
                + q * S * np.exp(-q * T) * norm.cdf(d1)
            ) / 365
        else:
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
            delta = -np.exp(-q * T) * norm.cdf(-d1)
            theta = (
                -(S * sigma * np.exp(-q * T) * norm.pdf(d1)) / (2 * np.sqrt(T))
                + r * K * np.exp(-r * T) * norm.cdf(-d2)
                - q * S * np.exp(-q * T) * norm.cdf(-d1)
            ) / 365

        gamma = (norm.pdf(d1) * np.exp(-q * T)) / (S * sigma * np.sqrt(T))
        vega = S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T) / 100
        rho = (K * T * np.exp(-r * T) * norm.cdf(d2 if option_type == "call" else -d2)) / 100

        return {
            "price": float(price),
            "delta": float(delta),
            "gamma": float(gamma),
            "vega": float(vega),
            "theta": float(theta),
            "rho": float(rho),
        }

    @staticmethod
    def binomial_tree(S, K, T, r, q, sigma, N=100, option_type="call", exercise="american"):
        dt = T / N
        u = np.exp(sigma * np.sqrt(dt))
        d = 1 / u
        p = (np.exp((r - q) * dt) - d) / (u - d)
        discount = np.exp(-r * dt)

        prices = S * (u ** np.arange(N, -1, -1)) * (d ** np.arange(0, N + 1))
        if option_type.lower() == "call":
            values = np.maximum(0, prices - K)
        else:
            values = np.maximum(0, K - prices)

        for i in range(N - 1, -1, -1):
            prices = S * (u ** np.arange(i, -1, -1)) * (d ** np.arange(0, i + 1))
            values = discount * (p * values[:-1] + (1 - p) * values[1:])
            if exercise.lower() == "american":
                if option_type.lower() == "call":
                    values = np.maximum(values, prices - K)
                else:
                    values = np.maximum(values, K - prices)

        return float(values[0])

    @staticmethod
    def implied_volatility(market_price, S, K, T, r, q, option_type="call"):
        def objective(sigma):
            if sigma <= 0:
                return 100.0
            return OptionEngine.black_scholes(S, K, T, r, q, sigma, option_type)["price"] - market_price

        try:
            return float(brentq(objective, 1e-5, 5.0))
        except ValueError:
            return None
