from cryptography.fernet import Fernet

def encrypt(key, plain_text):
    cipher_suite = Fernet(key)
    cipher_text = cipher_suite.encrypt(plain_text)
    return cipher_text

def decrypt(key, cipher_text):
    cipher_suite = Fernet(key)
    plain_text = cipher_suite.decrypt(cipher_text)
    return plain_text