"""
i_raw_content_storage.py

Description : interface of the raw content storage (object storage).
Rules       : content stored unchanged, addressed by its raw_hash only.
              The path is derived from the hash by the implementation; bucket and
              engine (local, MinIO, GCS, S3) are configuration.
              Writing an existing hash is useless: same hash = same content.
"""

from abc import ABC, abstractmethod


class IRawContentStorage(ABC):
    @abstractmethod
    async def exists(self, raw_hash: str) -> bool: ...

    @abstractmethod
    async def put(self, raw_hash: str, content: bytes) -> None: ...
