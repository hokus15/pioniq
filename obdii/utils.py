
def bytes_to_int_signed(b):
    """Convert big-endian signed integer bytearray to int."""
    return int.from_bytes(b, 'big', signed=True)
