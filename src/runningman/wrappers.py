def exception_handler(func, logger_index):
    def handeled_func(*args, **kwargs):
        logger = args[logger_index]
        try:
            func(*args, **kwargs)
        except:
            logger.exception("Logging uncaught exception")
            raise
    return handeled_func
