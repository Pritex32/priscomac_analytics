import hashlib
import platform
import uuid

def get_device_hash() -> str:
    """Generate a unique device hash based on hardware info."""
    raw = f"{platform.node()}-{platform.machine()}-{platform.processor()}-{uuid.getnode()}"
    return hashlib.sha256(raw.encode()).hexdigest()
