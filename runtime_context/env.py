"""
Usage:

1) declare your application-specific Env base class and add all
   application properties on this class either as properties or plain class attributes:

        class MyEnv:
            hostname = 'localhost'

            @property
            def username():
                return os.environ['MY_USERNAME']

2) Create a module-scope variable to store your RuntimeContext-aware env instance:

        env = RuntimeContextEnv.for_env(MyEnv)  # type: MyEnv

   If you have an existing instance of MyEnv, you can pass that too:

        env = RuntimeContextEnv.for_env(MyEnv())  # type: MyEnv

   The type-hint comment is crucial so that you can use PyCharm auto-complete feature on env.

   One limitation is that MyEnv must have all available names set as class attributes.
   This is necessary to be able to check existence of attributes without invoking @property initialisers.
   Attributes are checked against MyEnv class, not instance!

3) You can now use env.hostname and env.username from anywhere:

        with env(username='test_user'):
            assert env.hostname == 'localhost'
            assert env.username == 'test_user'

"""

from .runtime_context import RuntimeContext

_runtime_context_env_attrs = (
    'env',
    'runtime_context',
    'for_cli',
    '_env_has',

    '__call__',

    # Overrides, must list them so that they aren't delegated to RuntimeContext straight away
    'has',
    'get',
    'set',
)


class RuntimeContextEnv:

    def __init__(self, env=None, runtime_context=None):
        self.env = env
        self.runtime_context = runtime_context

        super().__init__()

    def _env_has(self, name):
        # It is crucial to not call hasattr(self.env, name) because that may
        # have unexpected side-effects in @property initialisers.
        # Instead we are checking existence of attribute on the custom Env class.
        # This means that custom Env classes MUST have all valid names set
        # as class attributes. Having them set on instance is NOT sufficient.
        return hasattr(self.env.__class__, name)

    def __getattribute__(self, name):
        if name in _runtime_context_env_attrs:
            return object.__getattribute__(self, name)

        elif name.startswith('__'):
            return object.__getattribute__(self, name)

        if self.runtime_context.has(name):
            return self.runtime_context.get(name)

        # [Hackery no. 01] To use the rewired Env @properties
        if name in self.__class__.__dict__:
            value = self.__class__.__dict__[name]
            if hasattr(value, '__get__'):
                return value.__get__(self, self.__class__)
            return value

        if self._env_has(name):
            return getattr(self.env, name)

        if hasattr(self.runtime_context, name):
            return getattr(self.runtime_context, name)

        # Attributes that user has set directly on instance
        if name in self.__dict__:
            return self.__dict__[name]

        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in _runtime_context_env_attrs:
            return object.__setattr__(self, name, value)

        elif self._env_has(name) or self.runtime_context.has(name):
            return self.runtime_context.set(name, value)

        # User should be allowed to use whatever attributes they want in
        # their Env instances.
        return object.__setattr__(self, name, value)

    def get(self, name, default=None):
        if self.runtime_context.has(name):
            return self.runtime_context.get(name, default=default)

        if self._env_has(name):
            return getattr(self.env, name, default)

        raise AttributeError(name)

    def has(self, name):
        if self.runtime_context.has(name):
            return True

        if self._env_has(name):
            return True

        return False

    def set(self, name, value):
        if self.has(name):
            return setattr(self, name, value)
        else:
            raise AttributeError(name)

    def __call__(self, **context_vars):
        for name in context_vars:
            if not self.has(name):
                raise AttributeError(name)
        return self.runtime_context(**context_vars)

    @classmethod
    def for_env(cls, env_or_cls, runtime_context_or_cls=RuntimeContext):
        if isinstance(runtime_context_or_cls, type):
            runtime_context_cls = runtime_context_or_cls
            runtime_context = runtime_context_or_cls()
        else:
            runtime_context = runtime_context_or_cls
            runtime_context_cls = runtime_context.__class__

        if isinstance(env_or_cls, type):
            env_cls = env_or_cls
            env_instance = env_cls()
            rc_env_cls = type(
                '{}_for_{}'.format(runtime_context_cls.__name__, env_cls.__name__),
                (cls, env_cls),
                {},
            )
        else:
            env_instance = env_or_cls
            env_cls = env_instance.__class__
            rc_env_cls = type(
                '{}_for_{}'.format(runtime_context_cls.__name__, env_cls.__name__),
                (cls, env_cls),
                {},
            )

        # [Hackery no. 01] To rewire env_cls properties so that "self" in their code
        # refers to the runtime-context aware env, not the underlying env instance.
        for k, v in env_cls.__dict__.items():
            if not hasattr(cls, k):
                setattr(rc_env_cls, k, v)

        return rc_env_cls(env=env_instance, runtime_context=runtime_context)
