import hashlib
import hmac
import os
import secrets


def generate_salt(length: int = 16) -> str:
    return secrets.token_hex(length)


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100_000)
    return digest.hex()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt), password_hash)


def sign_value(value: str, secret: str) -> str:
    signature = hmac.new(secret.encode('utf-8'), value.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature


def signed_cookie(value: str, secret: str) -> str:
    return f'{value}:{sign_value(value, secret)}'


def verify_signed_cookie(cookie_value: str, secret: str) -> str:
    if ':' not in cookie_value:
        return ''
    value, signature = cookie_value.rsplit(':', 1)
    if hmac.compare_digest(sign_value(value, secret), signature):
        return value
    return ''
