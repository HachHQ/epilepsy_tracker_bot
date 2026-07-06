import base64
import hashlib
import hmac
import logging

from config_data.config import load_config

cfg = load_config('.env')
logger = logging.getLogger(__name__)

SECRET_KEY = cfg.tg_bot.hmac_secret_key.encode('utf-8')

def pack_callback_data(uuid, profile_id, sender_id) -> str:
    cb_data_bytes = f"{uuid}|{profile_id}|{sender_id}".encode()
    signature = hmac.new(SECRET_KEY, cb_data_bytes, hashlib.sha256).digest()
    signature = signature[:8]
    final_payload = cb_data_bytes + b"|" + signature
    base64_payload = base64.urlsafe_b64encode(final_payload).decode()
    return base64_payload

def unpack_callback_data(encoded_data: str) -> str:
    action = encoded_data.split('|', 1)[0]
    decoded = base64.urlsafe_b64decode(encoded_data.split('|', 1)[1])
    *data_parts, signature = decoded.rsplit(b"|", 1)
    raw_data = b"|".join(data_parts)
    expected_signature = hmac.new(SECRET_KEY, raw_data, hashlib.sha256).digest()[:8]
    if not hmac.compare_digest(signature, expected_signature):
        logger.warning("Callback signature mismatch")
        return
    cb_data = b''.join(data_parts)
    cb_data = cb_data.decode("utf-8")
    return action + "|" + cb_data