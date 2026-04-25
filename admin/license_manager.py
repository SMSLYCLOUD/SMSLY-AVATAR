import uuid
import hashlib
import os
import platform
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

# A simple secret key for generating hashes. In a real-world scenario,
# this should be securely embedded and obfuscated within the binary.
SECRET_SALT = "D3LULU_PR0DUCT10N_S4LT_!@#"

def get_machine_id() -> str:
    """
    Generates a unique machine ID based on hardware.
    Combines MAC address and system info.
    """
    try:
        # Get MAC address
        mac_num = hex(uuid.getnode()).replace('0x', '').upper()
        mac = '-'.join(mac_num[i: i + 2] for i in range(0, 11, 2))

        # Get System Info
        system_info = f"{platform.system()}-{platform.machine()}-{platform.processor()}"

        # Combine and hash
        raw_id = f"{mac}|{system_info}"

        # Use SHA-256 to create a deterministic ID
        machine_id = hashlib.sha256(raw_id.encode('utf-8')).hexdigest()

        return machine_id
    except Exception as e:
        logger.error(f"Failed to generate machine ID: {e}")
        # Fallback to something that will definitely fail validation if hardware access fails
        return "UNKNOWN_MACHINE_ID"

def generate_expected_key(machine_id: str) -> str:
    """
    Generates the expected license key string for a given machine ID.
    """
    raw_key = f"{machine_id}|{SECRET_SALT}"
    return hashlib.sha512(raw_key.encode('utf-8')).hexdigest()

def verify_license(key_path: str = "license.key") -> bool:
    """
    Verifies if the license.key file contains the valid key for this machine.
    """
    if not os.path.exists(key_path):
        logger.error(f"License file '{key_path}' not found.")
        return False

    try:
        with open(key_path, 'r') as f:
            provided_key = f.read().strip()

        machine_id = get_machine_id()
        expected_key = generate_expected_key(machine_id)

        if provided_key == expected_key:
            return True
        else:
            return False

    except Exception as e:
        logger.error(f"Error reading license file: {e}")
        return False

if __name__ == "__main__":
    # If run directly, just print the machine ID
    print(f"Machine ID: {get_machine_id()}")
