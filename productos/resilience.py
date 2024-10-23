from tenacity import retry, stop_after_attempt, wait_fixed, before_sleep_log
import pybreaker
from logger import setup_logger
import logging

logger = setup_logger('productos_resilience')

retry_config = retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    before_sleep=before_sleep_log(logger, logging.INFO)
)

class LoggingCircuitBreaker(pybreaker.CircuitBreaker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_state = pybreaker.STATE_CLOSED  

    def call(self, func, *args, **kwargs):
        
        logger.info(f"Current Circuit State: {self.state}")

        self._last_state = self.state

        return super().call(func, *args, **kwargs)

cb = LoggingCircuitBreaker(fail_max=5, reset_timeout=15)



