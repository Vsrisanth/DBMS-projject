import random
import string
import re
from db import execute_query

def generate_ticket_number():
    """Generates a unique civic complaint ticket number like #CC-8421."""
    while True:
        digits = ''.join(random.choices(string.digits, k=4))
        ticket = f"#CC-{digits}"
        exists = execute_query("SELECT id FROM complaints WHERE ticket_number = %s", (ticket,), one=True)
        if not exists:
            return ticket

def validate_indian_phone(phone):
    """
    Validates and standardizes an Indian mobile phone number.
    Rules:
      - Exactly 10 digits long.
      - Must begin with a digit in the range [6-9].
      - Accepts optional country code prefixes: +91, 91, or 0.
    Returns:
      (is_valid: bool, normalized_10_digits: str or None)
    """
    if not phone:
        return False, None
    clean = re.sub(r'\D', '', str(phone))
    if clean.startswith('91') and len(clean) == 12:
        clean = clean[2:]
    elif clean.startswith('0') and len(clean) == 11:
        clean = clean[1:]
    if re.match(r'^[6-9]\d{9}$', clean):
        return True, clean
    return False, None
