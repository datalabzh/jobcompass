"""
__init__.py

Description : public API of the interfaces shared by the JobCompass bricks.
Rules       : bricks import only from here (from interfaces import ...).
              Interfaces only, no data contract (see contracts) and no
              business logic.
"""

from interfaces.i_use_case import IUseCase

__all__ = ["IUseCase"]
