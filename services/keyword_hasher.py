import bcrypt
import logging

logger = logging.getLogger(__name__)

class KeywordHasher:
    def hash_keyword(self, keyword: str) -> str:
        normalized_keyword = keyword.strip().lower()
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(normalized_keyword.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_keyword(self, keyword: str, hashed: str) -> bool:
        try:
            normalized_keyword = keyword.strip().lower()
            return bcrypt.checkpw(normalized_keyword.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error verifying keyword: {e}")
            return False