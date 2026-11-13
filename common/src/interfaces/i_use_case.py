"""
i_use_case.py

Description : what every use case of every brick provides: one public method,
              execute.
Rules       : a use case receives everything it needs when created (scraper,
              storage, settings...); execute runs it and returns its report.
              Everything else in a use case is private: callers (CLI, Dagster)
              only know execute.
"""

from abc import ABC, abstractmethod


class IUseCase(ABC):
    """A business action, run by execute()."""

    @abstractmethod
    def execute(self) -> object:
        """Run the use case and return its report."""
