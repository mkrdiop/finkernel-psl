from enum import Enum

class ContractState(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    OBSERVATION_PENDING = "OBSERVATION_PENDING"
    COUPON_EVALUATION = "COUPON_EVALUATION"
    AUTOCALL_TRIGGERED = "AUTOCALL_TRIGGERED"
    MATURED = "MATURED"
    TERMINATED = "TERMINATED"

class ContractStateMachine:
    def __init__(self, initial_state: ContractState = ContractState.CREATED):
        self.state = initial_state

    def transition(self, new_state: ContractState):
        valid_transitions = {
            ContractState.CREATED: [ContractState.ACTIVE],
            ContractState.ACTIVE: [ContractState.OBSERVATION_PENDING, ContractState.MATURED, ContractState.TERMINATED],
            ContractState.OBSERVATION_PENDING: [ContractState.COUPON_EVALUATION, ContractState.AUTOCALL_TRIGGERED, ContractState.ACTIVE],
            ContractState.COUPON_EVALUATION: [ContractState.ACTIVE, ContractState.AUTOCALL_TRIGGERED, ContractState.TERMINATED],
            ContractState.AUTOCALL_TRIGGERED: [ContractState.TERMINATED],
            ContractState.MATURED: [ContractState.TERMINATED],
            ContractState.TERMINATED: []
        }
        if new_state not in valid_transitions.get(self.state, []):
            raise ValueError(f"Invalid state transition from {self.state} to {new_state}")
        self.state = new_state
