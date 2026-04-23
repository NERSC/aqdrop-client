import httpx
from . import creds

def connect_verbose():
    try:
        print("Connecting...")
        from .main import AqdropClient
        c = AqdropClient()
        print(f"Connected to AQDROP service as user {creds.get_username()}.\n")
    except httpx.ConnectError as e:
        print("Could not connect to AQDROP service. Is environment variable AQDROP_HOSTNAME properly set?")
        print(f"Error: {e}")
        exit()
    return c
