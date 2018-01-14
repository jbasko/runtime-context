import pytest

from runtime_context import RuntimeContext, RuntimeContextEnv


class MyEnv:
    @property
    def username(self):
        return 'default_username'

    @property
    def password(self):
        raise ValueError('password not set')


def test_rc_env_from_env_cls():
    env2 = RuntimeContextEnv.for_env(MyEnv)  # type: MyEnv

    assert env2.username == 'default_username'
    with pytest.raises(ValueError):
        assert env2.password

    with env2(password='secret'):
        assert env2.username == 'default_username'
        assert env2.password == 'secret'


def test_rc_env_from_custom_env_instance():
    my_env = MyEnv()
    assert my_env.username == 'default_username'

    env = RuntimeContextEnv.for_env(my_env)

    assert env.username == 'default_username'
    with env(username='custom_username'):
        assert env.username == 'custom_username'


def test_rc_env_with_custom_rc_cls():
    class MyRuntimeContext(RuntimeContext):
        pass

    env1 = RuntimeContextEnv.for_env(MyEnv, MyRuntimeContext)
    assert isinstance(env1.runtime_context, MyRuntimeContext)

    env2 = RuntimeContextEnv.for_env(MyEnv, MyRuntimeContext())
    assert isinstance(env2.runtime_context, MyRuntimeContext)


def test_rc_env_setattr_sets_current_context_vars():
    env = RuntimeContextEnv.for_env(MyEnv)

    assert env.username == 'default_username'

    with env():
        assert env.username == 'default_username'

        env.username = 'custom_username'
        assert env.username == 'custom_username'

    assert env.username == 'default_username'


def test_reading_rc_env_from_context_should_not_touch_env_property_initialiser():
    class CustomEnv:
        @property
        def dont_touch_me(self):
            raise ValueError()

    env = RuntimeContextEnv.for_env(CustomEnv())

    assert env.has('dont_touch_me')

    with env():
        assert env.has('dont_touch_me')

        with pytest.raises(ValueError):
            assert env.dont_touch_me

        with pytest.raises(ValueError):
            assert env.get('dont_touch_me')

        with pytest.raises(ValueError):
            assert env.get('dont_touch_me', 42)

        with env(dont_touch_me=23):
            assert env.dont_touch_me == 23
            assert env.has('dont_touch_me')
            assert env.get('dont_touch_me') == 23

        assert env.has('dont_touch_me')

        with pytest.raises(ValueError):
            assert env.dont_touch_me


def test_env_is_strict():
    class CustomEnv:
        pass

    custom_env = CustomEnv()
    custom_env.c = 3  # should be inaccessible through RuntimeContextEnv because it is not a class attribute

    env = RuntimeContextEnv.for_env(custom_env)
    assert not env.has('c')

    with pytest.raises(AttributeError):
        _ = env.c  # noqa

    # Set directly on instance, not an env variable!
    env.c = 5
    assert env.c == 5
    assert not env.has('c')

    # Confirm in action
    with pytest.raises(AttributeError):
        with env(c=15):
            pass

    with pytest.raises(AttributeError):
        env.set('c', 15)

    with pytest.raises(AttributeError):
        env.get('c', 15)


def test_env_still_allows_vars_set_in_runtime_context():
    class CustomEnv:
        pass

    runtime_context = RuntimeContext()
    with runtime_context(dry_run=True):
        env = RuntimeContextEnv.for_env(CustomEnv(), runtime_context)
        assert env.dry_run is True
        assert env.has('dry_run')
        assert env.get('dry_run') is True
        assert env.get('dry_run', 5) is True

        env.dry_run = False
        assert env.dry_run is False
        assert env.get('dry_run') is False
        assert env.has('dry_run')

        with env(dry_run=555):
            assert env.dry_run == 555
            assert env.get('dry_run') == 555

            with env():
                env.set('dry_run', 777)
                assert env.dry_run == 777
                assert env.get('dry_run') == 777

        assert env.dry_run is False
        assert env.get('dry_run') is False
        assert env.has('dry_run')


def test_env_self_refers_to_rc_env_not_env():
    class CustomEnv:
        @property
        def greeting(self):
            return 'hello'

        @property
        def message(self):
            return '{} world!'.format(self.greeting)

    runtime_context = RuntimeContext()
    env = RuntimeContextEnv.for_env(CustomEnv, runtime_context)
    assert env.message == 'hello world!'

    with env(greeting='Goodbye'):
        assert env.message == 'Goodbye world!'

        with env():
            assert env.message == 'Goodbye world!'

            with env(message='No message'):
                assert env.message == 'No message'

                with env(greeting='Does not matter'):
                    assert env.message == 'No message'

            with env(greeting='Ciao'):
                assert env.message == 'Ciao world!'

        assert env.message == 'Goodbye world!'

    assert env.message == 'hello world!'


def test_env_init_is_not_broken():

    class CustomEnv:
        def __init__(self):
            self.x = 1

    env = RuntimeContextEnv.for_env(CustomEnv)
    assert env.x == 1
