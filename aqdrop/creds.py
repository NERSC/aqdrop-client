import os

def get_username():
    """Returns the value of the AQDROP_USERNAME environment variable.

    Raises:
        NameError: If AQDROP_USERNAME is not set.
    """
    username = os.getenv("AQDROP_USERNAME")
    if username is None:
        raise NameError("Environment variable AQDROP_USERNAME must be set!")
    return username

def get_password():
    """Returns the value of the AQDROP_PASSWORD environment variable.

    Raises:
        NameError: If AQDROP_PASSWORD is not set.
    """
    password = os.getenv("AQDROP_PASSWORD")
    if password is None:
        raise NameError("Environment variable AQDROP_PASSWORD must be set!")
    return password

def get_network():
    """Returns the value of the AQDROP_HOSTNAME environment variable.

    Raises:
        NameError: If AQDROP_HOSTNAME is not set.
    """
    network = os.getenv("AQDROP_HOSTNAME")
    if network is None:
        raise NameError("Environment variable AQDROP_HOSTNAME must be set!")
    return network
