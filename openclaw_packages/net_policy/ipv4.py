from .ip import is_canonical_dotted_decimal_ipv4


def validate_dotted_decimal_ipv4_input(value):
    if not value:
        return "IP address is required for custom bind mode"
    if is_canonical_dotted_decimal_ipv4(value):
        return None
    return "Invalid IPv4 address (e.g., 192.168.1.100)"


def validate_ipv4_address_input(value):
    return validate_dotted_decimal_ipv4_input(value)
