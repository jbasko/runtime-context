import threading

from hookery import HookRegistry

_thread_local = threading.local()
_thread_local.stack = []


class _ContextManager:
    def __init__(self, runtime_context, **context_vars):
        self.runtime_context = runtime_context
        self.context_vars = context_vars

    def __enter__(self):
        self.runtime_context._stack.append(self.context_vars)
        self.runtime_context.context_entered.trigger(context=self.runtime_context)
        return self.runtime_context

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.runtime_context._stack.pop()
        self.runtime_context.context_exited.trigger(context=self.runtime_context)


class RuntimeContext:
    """
    This is it.
    """

    def __init__(self):
        self._stack = _thread_local.stack
        self._hooks = HookRegistry(self)
        self.context_entered = self._hooks.register_event('context_entered')
        self.context_exited = self._hooks.register_event('context_exited')

    def __getattr__(self, name):
        """
        Attribute access is strict -- names not available in the stack will
        raise an AttributeError.
        """
        if self.is_context_var(name):
            return self.get(name)
        raise AttributeError(name)

    def get(self, name, default=None):
        for ctx in reversed(self._stack):
            if name in ctx:
                return ctx[name]
        return default

    def set(self, name, value):
        if not self._stack:
            raise RuntimeError('Trying to set context variable {!r} outside of runtime context'.format(name))
        self._stack[-1][name] = value

    def is_context_var(self, name):
        """
        Returns True if `name` is declared anywhere in the context stack.
        """
        return any(name in ctx for ctx in reversed(self._stack))

    def __call__(self, **context_vars):
        """
        Creates a new context manager upon entering which `context_vars` will be used
        to create a new context.
        """
        return _ContextManager(runtime_context=self, **context_vars)
