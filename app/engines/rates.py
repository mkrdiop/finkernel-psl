import QuantLib as ql
from datetime import datetime


class RatesEngine:
    @staticmethod
    def bootstrap_and_price_swap(val_date_str, notional, fixed_rate, swap_tenor_years, depo_rate, swap_rates):
        val_date = datetime.strptime(val_date_str, "%Y-%m-%d")
        ql_eval_date = ql.Date(val_date.day, val_date.month, val_date.year)
        ql.Settings.instance().evaluationDate = ql_eval_date

        calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
        settlement_date = calendar.advance(ql_eval_date, ql.Period(2, ql.Days))
        day_counter = ql.Actual360()

        helpers = [
            ql.DepositRateHelper(
                ql.QuoteHandle(ql.SimpleQuote(depo_rate)),
                ql.Period(3, ql.Months),
                2,
                calendar,
                ql.ModifiedFollowing,
                False,
                day_counter,
            ),
            ql.SwapRateHelper(
                ql.QuoteHandle(ql.SimpleQuote(swap_rates[0])),
                ql.Period(2, ql.Years),
                calendar,
                ql.Annual,
                ql.ModifiedFollowing,
                day_counter,
                ql.Sofr(),
            ),
            ql.SwapRateHelper(
                ql.QuoteHandle(ql.SimpleQuote(swap_rates[1])),
                ql.Period(5, ql.Years),
                calendar,
                ql.Annual,
                ql.ModifiedFollowing,
                day_counter,
                ql.Sofr(),
            ),
            ql.SwapRateHelper(
                ql.QuoteHandle(ql.SimpleQuote(swap_rates[2])),
                ql.Period(10, ql.Years),
                calendar,
                ql.Annual,
                ql.ModifiedFollowing,
                day_counter,
                ql.Sofr(),
            ),
        ]

        curve = ql.PiecewiseLogLinearDiscount(settlement_date, helpers, day_counter)
        curve_handle = ql.RelinkableYieldTermStructureHandle(curve)

        schedule = ql.Schedule(
            settlement_date,
            settlement_date + ql.Period(swap_tenor_years, ql.Years),
            ql.Period(ql.Annual),
            calendar,
            ql.ModifiedFollowing,
            ql.ModifiedFollowing,
            ql.DateGeneration.Forward,
            False,
        )

        swap = ql.VanillaSwap(
            ql.VanillaSwap.Payer,
            notional,
            schedule,
            fixed_rate,
            ql.Thirty360(ql.Thirty360.BondBasis),
            schedule,
            ql.Sofr(curve_handle),
            0.0,
            ql.Sofr(curve_handle).dayCounter(),
        )
        swap.setPricingEngine(ql.DiscountingSwapEngine(curve_handle))

        return {
            "npv": float(swap.NPV()),
            "fair_rate": float(swap.fairRate()),
            "maturity_date": str(settlement_date + ql.Period(swap_tenor_years, ql.Years)),
        }
