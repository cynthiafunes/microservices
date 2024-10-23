from tenacity import retry, stop_after_attempt, wait_fixed
import pybreaker

retry_config = retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1)
)

class SimpleCircuitBreaker(pybreaker.CircuitBreaker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _state_open(self):
        super()._state_open()

    def _state_closed(self):
        super()._state_closed()

    def _state_half_open(self):
        super()._state_half_open()

cb = SimpleCircuitBreaker(fail_max=5, reset_timeout=30)