import hashlib
import os

# DO NOT CHANGE THIS HASH.
# Doing so overrides the integrity of the certified V12 logic parity.
EXPECTED_V12_HASH = "7c3757d2de37a744d8275f969851829761302a03c65ff8d7c28720fc36c07feb"

def verify_core_integrity() -> bool:
    """
    Checks if parity_rules_v12.py has been modified by calculating its SHA256.
    Returns True if intact, False if tampered with.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    rules_path = os.path.join(current_dir, "parity_rules_v12.py")
    
    if not os.path.exists(rules_path):
        return False
        
    sha256_hash = hashlib.sha256()
    with open(rules_path, "rb") as f:
        # Normalizamos os line endings para garantir que o Hash seja idêntico
        # independente se o Git baixou em formato Windows (CRLF) ou Mac (LF).
        content = f.read().replace(b"\r\n", b"\n")
        sha256_hash.update(content)
            
    return sha256_hash.hexdigest() == EXPECTED_V12_HASH
