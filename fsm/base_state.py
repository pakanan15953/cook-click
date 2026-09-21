# -*- coding: utf-8 -*-
import time

class BaseState:
    """Base class for all FSM states with built-in lifecycle and watchdog timeout."""
    def __init__(self, context, timeout_seconds=30.0):
        self.ctx = context
        self.timeout_seconds = timeout_seconds
        self.enter_time = time.time()
        self.state_name = self.__class__.__name__

    def on_enter(self):
        """Called once when transitioning into this state."""
        self.enter_time = time.time()

    def execute(self, frame) -> "BaseState":
        """
        Executed on every frame update.
        Returns the next State instance, or self to remain in current state.
        """
        raise NotImplementedError("Each state must implement its execute method")

    def on_exit(self):
        """Called once when transitioning out of this state."""
        pass

    def is_timed_out(self, custom_timeout=None) -> bool:
        """Returns True if the state has been active longer than allowed."""
        limit = custom_timeout if custom_timeout is not None else self.timeout_seconds
        return (time.time() - self.enter_time) > limit

    def elapsed_time(self) -> float:
        """Returns seconds elapsed since entering this state."""
        return time.time() - self.enter_time
