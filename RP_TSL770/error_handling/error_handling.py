import logging

formatter = logging.Formatter("[{asctime}] [{levelname}] - {name} : {message}", 
                              "%Y-%m-%d %H:%M:%S", style = "{")

def exception_handler(logger):
    def decorator(function):
        def wrapper(*args, **kwargs):
            try:
                function(*args, **kwargs)
            except Exception as e:
                logger.error(e)
        return wrapper
    return decorator
