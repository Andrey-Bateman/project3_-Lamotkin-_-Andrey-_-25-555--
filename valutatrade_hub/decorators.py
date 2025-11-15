import functools
import logging
from datetime import datetime
from typing import Callable, Any

logger = logging.getLogger(__name__)

def log_action(action: str, verbose: bool = False):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                result = func(*args, **kwargs)
                log_msg = f"{action} user_id={args[0] if args else 'N/A'} result=OK"
                if verbose:
                    log_msg += f" details={result}"  
                logger.info(log_msg)
                return result
            except Exception as e:
                log_msg = f"{action} user_id={args[0] if args else 'N/A'} result=ERROR error_type={type(e).__name__} error_message={str(e)}"
                logger.error(log_msg)
                raise  
        return wrapper
    return decorator
