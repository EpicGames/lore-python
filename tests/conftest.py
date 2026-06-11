from lore.native import lore_log_configure
from lore.types import LoreLogConfig
from lore.types.enums import LoreLogLevel

lore_log_configure(LoreLogConfig(level=LoreLogLevel.DEBUG))
