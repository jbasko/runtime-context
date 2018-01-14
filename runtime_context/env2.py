"""
@runtime_context_env is a decorator for your custom Env class which may want to have its attributes overridden by
context variables.
"""
from .runtime_context import RuntimeContext


class EnvBase:
    _internals_ = (
        'get',
        'set',
        'runtime_context',
        'is_context_var',
    )

    runtime_context = None  # type: RuntimeContext

    def is_context_var(self, name):
        """
        Context variable is something that can be customised per context.
        This implementation only allows using such names that have an attribute
        with matching name set on the app-specific env class.
        """
        return not hasattr(EnvBase, name) and hasattr(self.__class__, name)

    def __call__(self, *args, **kwargs):
        return self.runtime_context(*args, **kwargs)

    def __getattribute__(self, name):
        if (name.startswith('__') and name.endswith('__')) or name in EnvBase._internals_:
            return object.__getattribute__(self, name)
        if self.is_context_var(name):
            if self.runtime_context.is_context_var(name):
                return self.runtime_context.get(name)
            # Fall back for attributes that haven't been env-customised
            return object.__getattribute__(self, name)
        elif name in self.__dict__:
            return object.__getattribute__(self, name)
        else:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in EnvBase._internals_:
            object.__setattr__(self, name, value)
        elif self.is_context_var(name):
            self.runtime_context.set(name, value)
        else:
            object.__setattr__(self, name, value)

    def get(self, name):
        if not self.is_context_var(name):
            raise AttributeError(name)
        return getattr(self, name)

    def set(self, name, value):
        if not self.is_context_var(name):
            raise AttributeError(name)
        setattr(self, name, value)


def runtime_context_env(env_cls):
    return type(env_cls.__name__, (env_cls, EnvBase), {
        'runtime_context': RuntimeContext(),
    })
