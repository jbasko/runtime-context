import collections
import threading

from hookery import Registry

_thread_local = threading.local()
_thread_local.stack = collections.defaultdict(list)


class Context(dict):
    """
    Dictionary of current state.

    Do not work with this directly, instead use RuntimeContextWrapper.

    Includes a link to the wrapper which created this Context, so this context is able
    to pop itself from the stack.
    """

    def __init__(self, wrapper: 'RuntimeContextWrapper', context_vars: dict):
        super().__init__(context_vars)
        self.wrapper = wrapper

    def __enter__(self):
        self._push_context()
        return self.wrapper

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._pop_context()

    def _push_context(self):
        self.wrapper._stack.append(self)
        self.wrapper.context_entered(context_vars=self)

    def _pop_context(self):
        assert self.wrapper.current is self
        self.wrapper._stack.pop()
        self.wrapper.context_exited(context_vars=self)


class RuntimeContextWrapper:
    """
    The main interface to work with runtime contexts.

    Create one instance of this per project and then do everything through it.
    """

    _internals_ = (
        '_stack',
        '_hookery',
        'context_entered',
        'context_exited',
    )

    def __init__(self):
        # Stack is wrapper-instance specific, so there can be multiple unrelated stacks per thread.
        self._stack = _thread_local.stack[self]

        self._hookery = Registry()
        self.context_entered = self._hookery.register_event('context_entered')
        self.context_exited = self._hookery.register_event('context_exited')

        # It simplifies life a lot if there is always one context present for each wrapper.
        self.push_context()

    def __getattr__(self, name):
        """
        Attribute access is strict -- names not available in the stack will
        raise an AttributeError. Use the .get() method for non-strict access.
        """
        if self.is_context_var(name):
            return self.get(name)
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in self._internals_:
            object.__setattr__(self, name, value)
        else:
            self.set(name, value)

    def __delattr__(self, name):
        if name in self._internals_:
            raise AttributeError('{!r} should not be deleted'.format(name))
        elif self.is_context_var(name):
            return self.reset(name)
        else:
            return object.__delattr__(self, name)

    def get(self, name, default=None):
        for ctx in reversed(self._stack):
            if name in ctx:
                return ctx[name]
        return default

    def set(self, name, value):
        self.current[name] = value

    def reset(self, name):
        """
        Resets the value of a var in the current context.
        """
        if name in self.current:
            del self.current[name]

    def reset_context(self):
        """
        Clears current context state
        """
        self.current.clear()

    def push_context(self, context_vars_dict=None, **context_vars):
        self.new_context(context_vars_dict=context_vars_dict, **context_vars)._push_context()

    def pop_context(self):
        self.current._pop_context()

    @property
    def current(self):
        if not self._stack:
            raise RuntimeError('Trying to get current context while outside of runtime context')
        return self._stack[-1]

    def is_context_var(self, name):
        """
        Returns True if `name` is declared anywhere in the context stack.
        """
        return any(name in ctx for ctx in reversed(self._stack))

    def __call__(self, context_vars_dict=None, **context_vars):
        return self.new_context(context_vars_dict=context_vars_dict, **context_vars)

    def new_context(self, context_vars_dict=None, **context_vars):
        context_vars = context_vars_dict or context_vars
        return Context(self, context_vars)
