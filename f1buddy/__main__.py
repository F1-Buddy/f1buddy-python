import logging

from . import config
from .bot import F1Buddy


def main():
    cfg = config.load()
    logging.basicConfig(level=cfg.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    F1Buddy(cfg).run(cfg.token, log_handler=None)


if __name__ == "__main__":
    main()
