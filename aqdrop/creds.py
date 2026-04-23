import os

def get_username():
    username = os.getenv("AQDROP_USERNAME")
    if username is None:
        raise NameError("Environment variable AQDROP_USERNAME must be set!")
    return username

def get_password():
    password = os.getenv("AQDROP_PASSWORD")
    if password is None:
        raise NameError("Environment variable AQDROP_PASSWORD must be set!")
    return password

def get_network():
    network = os.getenv("AQDROP_HOSTNAME")
    if network is None:
        raise NameError("Environment variable AQDROP_HOSTNAME must be set!")
    return network
