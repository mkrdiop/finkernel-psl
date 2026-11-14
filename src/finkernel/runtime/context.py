from typing import List, Dict, Any
from finkernel.fir.models import FIRModel
from finkernel.runtime.state_machine import ContractStateMachine, ContractState
from finkernel.runtime.cashflows import CashflowRecord

class ExecutionContext:
    def __init__(self, fir: FIRModel):
        self.fir = fir
        self.state_machine = ContractStateMachine(ContractState.CREATED)
        self.cashflows: List[CashflowRecord] = []
        self.unpaid_memory_coupons: float = 0.0
        self.is_terminated = False

    def add_cashflow(self, cf: CashflowRecord):
        self.cashflows.append(cf)
