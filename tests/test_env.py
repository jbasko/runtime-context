import collections
from typing import Union  # noqa

import pytest

from runtime_context import EnvBase, runtime_context_env  # noqa


@pytest.fixture
def xy_app():
    @runtime_context_env
    class App:
        x = 1
        y = 2

    app = App()
    yield app


def test_all():
    @runtime_context_env
    class App:
        x = 0
        y = 1

        def __init__(self):
            super().__init__()
            self.z = 2

    app = App()
    assert app.is_context_var('x')
    assert app.is_context_var('y')
    assert not app.is_context_var('z')

    assert app.x == 0
    assert 'x' not in app.__dict__
    assert app.get('x') == 0

    assert app.y == 1
    assert 'y' not in app.__dict__
    assert app.get('y') == 1

    assert app.z == 2
    assert app.__dict__['z'] == 2
    with pytest.raises(AttributeError):
        assert app.get('z')

    with app(y=11):
        assert app.x == 0
        assert app.y == 11
        assert app.z == 2

        app.x = 1000
        assert 'x' not in app.__dict__
        assert app.x == 1000
        assert app.get('x') == 1000

        app.y = 111
        assert 'y' not in app.__dict__
        assert app.y == 111
        assert app.get('y') == 111

        app.z = 22
        assert app.__dict__['z'] == 22
        assert app.z == 22
        with pytest.raises(AttributeError):
            app.get('z')

        with app(y=1111):
            assert app.x == 1000
            assert app.y == 1111
            assert app.z == 22

            app.set('x', 2000)
            assert app.x == 2000

            app.set('y', 9999)
            assert app.y == 9999

            with pytest.raises(AttributeError):
                app.set('z', 222)

        assert app.x == 1000
        assert app.y == 111
        assert app.z == 22

    assert app.x == 0
    assert app.y == 1
    assert app.z == 22  # not a context variable, so isn't reset


def test_app_with_inheritance():
    class BaseApp:
        x = 0

    @runtime_context_env
    class App(BaseApp):
        y = 1

        def __init__(self):
            self.z = 2

    app = App()
    assert app.is_context_var('x')
    assert app.is_context_var('y')
    assert not app.is_context_var('z')

    assert app.get('x') == 0
    assert app.get('y') == 1


def test_env_example():
    dummy_config_files = {
        'config.json': {
            'db_name': 'stuff',
        },
        'config.ini': {
            'db_name': 'products',
        },
    }

    @runtime_context_env
    class YourAppEnv:
        config_file = None
        db_name = None

    env = YourAppEnv()  # type: Union[YourAppEnv, EnvBase]

    @env.context_var_set.listener(predicate=lambda name: name == 'config_file')
    def config_file_updated():
        if not env.config_file:
            return

        # print('Loading new config from {}'.format(env.config_file))
        for name, value in dummy_config_files[env.config_file].items():
            env.set(name, value)

    with env():
        assert env.db_name is None

        env.config_file = 'config.json'
        assert env.db_name == 'stuff'

        with env(config_file='config.ini'):
            assert env.db_name == 'products'

            env.db_name = 'products_modified'
            assert env.db_name == 'products_modified'

        assert env.db_name == 'stuff'

    assert env.db_name is None


def test_env_can_access_runtime_context_events(xy_app):
    calls = []

    @xy_app.context_entered.listener
    def context_entered(context_vars):
        calls.append(('context_entered', context_vars))

    @xy_app.context_exited.listener
    def context_exited(context_vars):
        calls.append(('context_exited', context_vars))

    assert calls == []

    with xy_app(x=1):
        with xy_app(y=2):
            pass

    assert calls == [
        ('context_entered', {'x': 1}),
        ('context_entered', {'y': 2}),
        ('context_exited', {'y': 2}),
        ('context_exited', {'x': 1}),
    ]


def test_reset_context(xy_app):

    with xy_app():
        assert xy_app.x == 1
        assert xy_app.y == 2
        xy_app.reset_context()

        assert xy_app.x == 1
        assert xy_app.y == 2

        xy_app.x = 11
        assert xy_app.x == 11

        xy_app.reset_context()
        assert xy_app.x == 1

        with xy_app(y=22):
            assert xy_app.y == 22

            xy_app.reset_context()
            assert xy_app.y == 2


def test_context_var_reset_event(xy_app):
    resets = []

    @xy_app.context_var_reset.listener
    def context_var_reset(name):
        resets.append(name)

    assert [] == resets

    with xy_app():
        pass

    assert [] == resets

    with xy_app(x=111):
        with xy_app():
            assert [] == resets

        assert [] == resets

    assert ['x'] == resets

    # Same value does not have any effect, it still is a reset
    with xy_app(x=1, y=2):
        assert ['x'] == resets

    # Can't compare the list because of Python 3.5
    counter = collections.Counter(resets)
    assert counter['x'] == 2
    assert counter['y'] == 1


def test_single_context_var_reset_with_reset_method(xy_app):
    assert xy_app.x == 1

    xy_app.reset('x')
    assert xy_app.x == 1  # cannot reset the default value

    with xy_app(x=111):
        assert xy_app.x == 111
        xy_app.reset('x')

        assert xy_app.x == 1

        with xy_app(x=111111):
            assert xy_app.x == 111111

            xy_app.reset('x')
            assert xy_app.x == 1

        assert xy_app.x == 1

    assert xy_app.x == 1


def test_single_context_var_reset_with_delattr(xy_app):
    assert xy_app.x == 1

    del xy_app.x
    del xy_app.x

    assert xy_app.x == 1  # cannot reset the default value

    with xy_app(x=111):
        assert xy_app.x == 111

        with xy_app(x=111111):
            assert xy_app.x == 111111

            del xy_app.x
            assert xy_app.x == 111

            del xy_app.x
            assert xy_app.x == 111  # cannot reset the default that is beyond current stack

        assert xy_app.x == 111

        del xy_app.x
        assert xy_app.x == 1

    assert xy_app.x == 1


def test_single_context_var_reset_triggers_reset_event(xy_app):
    resets = []

    @xy_app.context_var_reset.listener
    def context_var_reset(name):
        resets.append(name)

    with xy_app():
        with xy_app():
            pass

    assert [] == resets

    with xy_app(x=111):
        assert [] == resets

        xy_app.reset('x')
        assert ['x'] == resets

        del xy_app.x
        assert ['x', 'x'] == resets

    # a new reset isn't triggered because x was no longer in the context
    assert ['x', 'x'] == resets
