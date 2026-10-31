from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """Common parent of every contract.

    Carries no fields, only the rules shared by all contracts:
    - frozen: a contract instance cannot be modified once created;
    - extra="forbid": any field not declared in the contract is rejected.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
