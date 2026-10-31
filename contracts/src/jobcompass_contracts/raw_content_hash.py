"""
raw_content_hash.py

Description : computes the raw_hash of a fetched content, as defined by the RawOffer
              contract.
Rules       : raw_hash = SHA-256 of the uncompressed content, as lowercase hex
              (64 characters).
              Every brick computes it with this function, so the same content always
              gets the same hash and the same storage path.
"""

import hashlib


def compute_raw_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
