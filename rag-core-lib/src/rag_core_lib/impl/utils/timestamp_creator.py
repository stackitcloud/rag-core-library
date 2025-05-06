from datetime import datetime


def create_timestamp() -> str:
    """
    Create a timestamp string in the format YYYYMMDDHHMMSS.

    Returns
    -------
    str
        The current timestamp in the format YYYYMMDDHHMMSS.
    """
    return datetime.now().strftime("%Y%m%d%H%M%S")
