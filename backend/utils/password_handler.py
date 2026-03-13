import bcrypt


class PasswordHandler:
    """
    Direct bcrypt — passlib wrapper hata diya (Python 3.13 + new bcrypt incompatible).
    Constant-time comparison preserved — timing attack safe.
    """

    _ENCODING = "utf-8"
    _MAX_BYTES = 72  # bcrypt hard limit — silently truncates beyond this

    @staticmethod
    def hash(password: str) -> str:
        password_bytes = password.encode(PasswordHandler._ENCODING)[:PasswordHandler._MAX_BYTES]
        salt = bcrypt.gensalt(rounds=12)  # rounds=12 — industry standard for prod
        return bcrypt.hashpw(password_bytes, salt).decode(PasswordHandler._ENCODING)

    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        try:
            password_bytes = plain_password.encode(PasswordHandler._ENCODING)[:PasswordHandler._MAX_BYTES]
            return bcrypt.checkpw(password_bytes, hashed_password.encode(PasswordHandler._ENCODING))
        except Exception:
            return False  # never raise on verify — just return False