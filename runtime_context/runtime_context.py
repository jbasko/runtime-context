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
    def __init__(self):
        self._stack = _thread_local.stack
        self._hooks = HookRegistry(self)
        self.context_entered = self._hooks.register_event('context_entered')
        self.context_exited = self._hooks.register_event('context_exited')

    def __getattr__(self, name):
        return self.get(name)

    def get(self, name, default=None):
        for ctx in reversed(self._stack):
            if name in ctx:
                return ctx[name]
        return default

    def set(self, name, value):
        if not self.supports(name):
            raise AttributeError(name)
        if not self._stack:
            raise RuntimeError('Trying to set context variable {!r} outside of runtime context'.format(name))
        self._stack[-1][name] = value

    def has(self, name):
        return any(name in ctx for ctx in reversed(self._stack))

    def has_own(self, name):
        return self._stack and name in self._stack[-1]

    def __call__(self, **context_vars):
        return _ContextManager(runtime_context=self, **context_vars)


class RuntimeContextEnv:
    """
    Base class for application-specific RuntimeContext-aware Env classes.

    The basic usage is as follows:

    1) declare your application-specific Env base class which extends object and add all
       application properties on this class either as properties or plain class attributes:

        class MyEnv:
            hostname = 'localhost'

            @property
            def username():
                return os.environ['MY_USERNAME']

    2) declare RuntimeContext-aware Env class that extends RuntimeContextEnv and mixes in MyEnv.
       This way you will tell your IDE that your env has all the properties of MyEnv, but the
       values will actually be provided dynamically by RuntimeContextEnv.__getattribute__.

        class MyRuntimeContextEnv(RuntimeContextEnv, MyEnv):
            env_cls = MyEnv

        env = MyRuntimeContextEnv()

        You want to do this kind of declaration because this will help your IDE help you!

    3) You can now use env.hostname and env.username from anywhere.

    """

    env_cls = None
    runtime_context_cls = RuntimeContext

    def __init__(self, env=None, runtime_context=None):
        super().__init__()
        self.env = env or self.env_cls()
        self.runtime_context = runtime_context or self.runtime_context_cls()

    def __getattribute__(self, item):
        # TODO This is imperfect. Needs testing and documentation.
        # TODO Why did PyCharm stop autocompleting env?

        if item in ('env', 'env_cls', 'runtime_context', 'runtime_context_cls', 'for_cli', '__call__'):
            return object.__getattribute__(self, item)
        elif item.startswith('__'):
            return object.__getattribute__(self, item)

        # Must not call hasattr on env because that may invoke [cached]properties
        # which we should not do if runtime_context overrides any.
        if self.runtime_context.has(item):
            return self.runtime_context.get(item)

        if hasattr(self.env, item):
            return getattr(self.env, item)

        raise AttributeError(item)

    def __call__(self, **context_vars):
        return self.runtime_context(**context_vars)

    def for_cli(self, cli_args):
        """
        Creates a context manager with only non-None CLI args set in runtime context.
        """
        context = {k: v for k, v in cli_args.__dict__.items() if v is not None}
        return self.runtime_context(**context)
