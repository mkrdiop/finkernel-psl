import numpy as np
from typing import Dict, Any


class PayoffExecutionEngine:
    @staticmethod
    def simulate_phoenix_ir(
        ir: Dict[str, Any],
        spot_prices: np.ndarray,
        volatilities: np.ndarray,
        correl_matrix: np.ndarray,
        risk_free_rate: float = 0.035,
        num_paths: int = 50000,
        seed: int = 42,
    ) -> Dict[str, Any]:
        np.random.seed(seed)

        notional = float(ir["notional"])
        num_assets = len(spot_prices)

        comps = {c["id"]: c for c in ir["components"]}
        coupon_comp = comps.get("coupon", {})
        autocall_comp = comps.get("autocall", {})
        cap_comp = comps.get("capital_redemption", {})

        annual_coupon = float(coupon_comp.get("annual_rate", 0.08))
        coupon_barrier = float(coupon_comp.get("condition", {}).get("threshold", 0.70))
        memory_enabled = bool(coupon_comp.get("memory", True))

        autocall_enabled = bool(autocall_comp)
        autocall_start = int(autocall_comp.get("eligibility", {}).get("start_observation", 2))
        autocall_barrier = float(autocall_comp.get("trigger", {}).get("threshold", 1.00))

        ki_barrier = float(cap_comp.get("barrier", {}).get("level", 0.60))

        freq = ir["dates"]["schedule"].get("observation_schedule", {}).get("frequency", "quarterly")
        steps_per_year = 4 if freq == "quarterly" else (2 if freq == "semiannual" else 1)
        years = 5.0
        num_steps = int(years * steps_per_year)
        dt = 1.0 / steps_per_year
        coupon_per_period = annual_coupon / steps_per_year

        L = np.linalg.cholesky(correl_matrix)
        paths = np.zeros((num_paths, num_steps + 1, num_assets))
        paths[:, 0, :] = spot_prices

        for t in range(1, num_steps + 1):
            Z = np.random.standard_normal((num_paths, num_assets))
            W = Z @ L.T
            drift = (risk_free_rate - 0.5 * volatilities**2) * dt
            diffusion = volatilities * np.sqrt(dt) * W
            paths[:, t, :] = paths[:, t - 1, :] * np.exp(drift + diffusion)

        discounted_payoffs = np.zeros(num_paths)
        active_mask = np.ones(num_paths, dtype=bool)
        unpaid_coupons = np.zeros(num_paths)
        autocall_count = 0
        ki_breach_count = 0

        for step in range(1, num_steps + 1):
            t_years = step * dt
            df = np.exp(-risk_free_rate * t_years)

            norm_perf = paths[:, step, :] / spot_prices
            worst_perf = np.min(norm_perf, axis=1)

            coupon_hit = active_mask & (worst_perf >= coupon_barrier)
            coupon_miss = active_mask & (worst_perf < coupon_barrier)

            paid_now = np.where(
                coupon_hit,
                notional * (coupon_per_period + (unpaid_coupons if memory_enabled else 0.0)),
                0.0,
            )
            discounted_payoffs += paid_now * df

            if memory_enabled:
                unpaid_coupons = np.where(
                    coupon_hit,
                    0.0,
                    np.where(coupon_miss, unpaid_coupons + coupon_per_period, unpaid_coupons),
                )

            if autocall_enabled and step >= autocall_start:
                ac_hit = active_mask & (worst_perf >= autocall_barrier)
                discounted_payoffs += np.where(ac_hit, notional * df, 0.0)
                autocall_count += int(np.sum(ac_hit))
                active_mask = active_mask & (~ac_hit)

            if step == num_steps:
                ki_breached = active_mask & (worst_perf < ki_barrier)
                safe_maturity = active_mask & (worst_perf >= ki_barrier)

                discounted_payoffs += np.where(safe_maturity, notional * df, 0.0)
                discounted_payoffs += np.where(ki_breached, notional * worst_perf * df, 0.0)
                ki_breach_count = int(np.sum(ki_breached))

        fair_value = float(np.mean(discounted_payoffs))
        std_error = float(np.std(discounted_payoffs) / np.sqrt(num_paths))

        return {
            "product_id": ir["product_id"],
            "canonical_hash": ir["canonical_hash"],
            "fair_value": round(fair_value, 2),
            "price_pct": round((fair_value / notional) * 100.0, 2),
            "mc_std_error": round(std_error, 4),
            "autocall_probability": round(autocall_count / num_paths, 4),
            "ki_breach_probability": round(ki_breach_count / num_paths, 4),
            "paths_simulated": num_paths,
        }
