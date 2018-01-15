__version__ = '1.2.1'

from .env2 import runtime_context_env
from .runtime_context import RuntimeContext

__all__ = [
    'RuntimeContext',
    'runtime_context_env',
]
