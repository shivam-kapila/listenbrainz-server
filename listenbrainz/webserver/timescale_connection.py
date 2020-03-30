import time
from listenbrainz.listenstore import TimescaleListenStore

_ts = None

def init_ts_connection(logger, conf):
    global _ts
    while True:
        logger.error("ys")
        try:
            _ts = TimescaleListenStore(conf, logger)
            break
        except Exception as e:
            logger.error("Couldn't create TimescaleListenStore instance: {}, sleeping and trying again...".format(str(e)), exc_info=True)
            time.sleep(2)

    logger.info("Successfully created TimescaleListenStore instance!")
    return _ts
