"""
contract_model.py

Description : common parent of every contract.
Rules       : carries no field, only the rules shared by all contracts.
              Frozen: a contract instance cannot be modified once created.
              extra="forbid": any field not declared in the contract is rejected.
"""

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
