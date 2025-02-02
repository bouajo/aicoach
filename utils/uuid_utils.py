"""
Utilities for UUID generation and handling.
"""

import uuid
from typing import Optional

def phone_to_uuid(phone_number: str, prefix: Optional[str] = "wa") -> str:
    """
    Convert phone number to a deterministic UUID using NAMESPACE_DNS.
    
    Args:
        phone_number: The phone number to convert
        prefix: Optional prefix to add to the phone number before hashing (e.g., "wa" for WhatsApp)
        
    Returns:
        str: A deterministic UUID based on the phone number
    """
    # Clean the phone number
    clean_number = phone_number.strip().replace("+", "")
    
    # Add prefix if provided
    if prefix:
        namespace_string = f"{prefix}_{clean_number}"
    else:
        namespace_string = clean_number
        
    # Generate UUID
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, namespace_string)) 