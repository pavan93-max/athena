# athena/utils.py
import os

def load_env(path=".env"):
    from dotenv import load_dotenv
    load_dotenv(path)
