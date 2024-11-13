import hashlib

def verifying_hash(msg)->bool:
    message = msg[:-32]
    return msg[-32:]==calculate_hash(message)

def add_hash(msg:bytes)->bytes:
    return msg + calculate_hash(msg)

def calculate_hash(msg:bytes)->bytes:
    hash_obj = hashlib.sha256()
    hash_obj.update(msg)
    hash_digest = hash_obj.digest()
    return hash_digest