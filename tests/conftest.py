import pytest

from lore.native import lore_log_configure, lore_shutdown
from lore.types import LoreLogConfig
from lore.types.enums import LoreLogLevel

lore_log_configure(LoreLogConfig(level=LoreLogLevel.DEBUG))


@pytest.fixture(scope="session", autouse=True)
def lore_runtime():
    """Shut lorelib down exactly once, after the whole session.

    The runtime cannot be restarted once stopped (lore.h: "Call this once, when
    no further calls will be made"), and any call made afterwards blocks forever
    instead of returning an error, so shutting down per test hangs the suite.
    """
    yield
    lore_shutdown()
