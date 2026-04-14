import hashlib
import os

# DO NOT CHANGE THIS HASH.
# Doing so overrides the integrity of the V11.6 logic parity.
EXPECTED_V11_HASH = "fba954782f90c5fc817ce876b79dce64e73fb2c2f0b5b5cf39c5796b6cf10f7c"

def verify_core_integrity() -> bool:
    """
    Checks if parity_rules_v11.py has been modified by calculating its SHA256.
    Returns True if intact, False if tampered with.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    rules_path = os.path.join(current_dir, "parity_rules_v11.py")
    
    if not os.path.exists(rules_path):
        return False
        
    sha256_hash = hashlib.sha256()
    with open(rules_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
            
    return sha256_hash.hexdigest() == EXPECTED_V11_HASH
