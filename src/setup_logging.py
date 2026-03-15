import logging


def setup_logger(log_file: str = "logs.log") -> None:
    """
    Configure le logger global.

    Parameters
    ----------
    log_file : str
        Chemin du fichier log
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )