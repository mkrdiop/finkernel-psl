import uuid
from typing import Dict, Any, List
import numpy as np
from finkernel.fir.models import FIRModel
from finkernel.runtime.context import ExecutionContext
from finkernel.runtime.state_machine import ContractState
from finkernel.runtime.cashflows import CashflowRecord
from finkernel.runtime.events import EventScheduler

class FinancialExecutionRuntime:
    @staticmethod
    def execute_simulation(fir: FIRModel, asset_spot_paths: np.ndarray, initial_spots: np.ndarray) -> Dict[str, Any]:
        ctx = ExecutionContext(fir)
        ctx.state_machine.transition(ContractState.ACTIVE)

        notional = fir.notional
        currency = fir.currency
        
        comps = {c["id"]: c for c in fir.components}
        coupon_comp = comps.get("coupon", {})
        autocall_comp = comps.get("autocall", {})
        cap_comp = comps.get("capital_redemption", {})

        annual_rate = float(coupon_comp.get("annual_rate", 0.08))
        freq = fir.schedule.get("observation_schedule", {}).get("frequency", "quarterly")
        steps_per_year = 4 if freq == "quarterly" else 2
        coupon_per_period = annual_rate / steps_per_year
        coupon_threshold = float(coupon_comp.get("condition", {}).get("threshold", 0.70))
        memory_enabled = bool(coupon_comp.get("memory", {}).get("enabled", True))

        autocall_enabled = bool(autocall_comp)
        autocall_start_obs = int(autocall_comp.get("eligibility", {}).get("start_observation", 2))
        autocall_threshold = float(autocall_comp.get("trigger", {}).get("threshold", 1.00))

        ki_barrier = float(cap_comp.get("barrier", {}).get("level", 0.60))

        obs_dates = EventScheduler.generate_observation_dates(
            fir.inception_date, fir.maturity_date, freq
        )

        for idx, obs_date in enumerate(obs_dates):
            if ctx.is_terminated:
                break

            obs_step = idx + 1
            ctx.state_machine.transition(ContractState.OBSERVATION_PENDING)

            spots_at_obs = asset_spot_paths[idx]
            performances = spots_at_obs / initial_spots
            worst_perf = float(np.min(performances))

            ctx.state_machine.transition(ContractState.COUPON_EVALUATION)

            if worst_perf >= coupon_threshold:
                total_coupon = notional * (coupon_per_period + ctx.unpaid_memory_coupons)
                ctx.unpaid_memory_coupons = 0.0
                
                cf = CashflowRecord(
                    cashflow_id=f"CF-{uuid.uuid4().hex[:8].upper()}",
                    product_id=fir.product_id,
                    generation_date=obs_date,
                    payment_date=obs_date,
                    amount=round(total_coupon, 2),
                    currency=currency,
                    category="coupon",
                    origin_event=f"Observation_{obs_step}",
                    rule_id="memory_coupon"
                )
                ctx.add_cashflow(cf)
            else:
                if memory_enabled:
                    ctx.unpaid_memory_coupons += coupon_per_period

            if autocall_enabled and obs_step >= autocall_start_obs:
                if worst_perf >= autocall_threshold:
                    ctx.state_machine.transition(ContractState.AUTOCALL_TRIGGERED)
                    
                    redemption_cf = CashflowRecord(
                        cashflow_id=f"CF-{uuid.uuid4().hex[:8].upper()}",
                        product_id=fir.product_id,
                        generation_date=obs_date,
                        payment_date=obs_date,
                        amount=round(notional, 2),
                        currency=currency,
                        category="redemption",
                        origin_event=f"Autocall_{obs_step}",
                        rule_id="autocall_redemption"
                    )
                    ctx.add_cashflow(redemption_cf)
                    ctx.state_machine.transition(ContractState.TERMINATED)
                    ctx.is_terminated = True
                    break

            ctx.state_machine.transition(ContractState.ACTIVE)

        if not ctx.is_terminated:
            ctx.state_machine.transition(ContractState.MATURED)
            final_spots = asset_spot_paths[-1]
            final_perf = float(np.min(final_spots / initial_spots))

            if final_perf >= ki_barrier:
                redemption_amount = notional
                rule = "capital_protection_safe"
            else:
                redemption_amount = notional * final_perf
                rule = "capital_protection_breached"

            maturity_cf = CashflowRecord(
                cashflow_id=f"CF-{uuid.uuid4().hex[:8].upper()}",
                product_id=fir.product_id,
                generation_date=fir.maturity_date,
                payment_date=fir.maturity_date,
                amount=round(redemption_amount, 2),
                currency=currency,
                category="redemption",
                origin_event="Maturity",
                rule_id=rule
            )
            ctx.add_cashflow(maturity_cf)
            ctx.state_machine.transition(ContractState.TERMINATED)
            ctx.is_terminated = True

        return {
            "product_id": fir.product_id,
            "final_state": ctx.state_machine.state.value,
            "total_cashflows": len(ctx.cashflows),
            "cashflows": [cf.model_dump() for cf in ctx.cashflows]
        }
