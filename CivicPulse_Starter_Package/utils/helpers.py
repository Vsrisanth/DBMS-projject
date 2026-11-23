import random
import string
from db import execute_query

def generate_ticket_number():
    """Generates a unique civic complaint ticket number like #CC-8421."""
    while True:
        digits = ''.join(random.choices(string.digits, k=4))
        ticket = f"#CC-{digits}"
        exists = execute_query("SELECT id FROM complaints WHERE ticket_number = %s", (ticket,), one=True)
        if not exists:
            return ticket
