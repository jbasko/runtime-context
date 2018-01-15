import pytest

from runtime_context.env2 import runtime_context_env


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


def test_change_hooks():
    @runtime_context_env
    class App:
        config_file = 'config.json'
        x = None

        def __init__(self):
            super().__init__()
            self.times_reloaded = 0

        def reload_config(self):
            self.times_reloaded += 1

    app = App()

    @app.context_var_updated.listener(predicate=lambda name: name == 'config_file')
    def reload_local_config():
        app.reload_config()

    with app():
        with app(x=1):
            assert app.times_reloaded == 0
            with app(config_file='config.yaml'):
                assert app.times_reloaded == 1

            assert app.times_reloaded == 2

        assert app.times_reloaded == 2

        app.config_file = 'config.txt'
        assert app.times_reloaded == 3

        with app():
            assert app.times_reloaded == 3
        assert app.times_reloaded == 3

    assert app.times_reloaded == 4


def test_env_can_access_runtime_context_events():
    @runtime_context_env
    class App:
        pass

    app = App()
    calls = []

    @app.context_entered.listener
    def context_entered(context_vars):
        calls.append(('context_entered', context_vars))

    @app.context_exited.listener
    def context_exited(context_vars):
        calls.append(('context_exited', context_vars))

    assert calls == []

    with app(x=1):
        with app(y=2):
            pass

    assert calls == [
        ('context_entered', {'x': 1}),
        ('context_entered', {'y': 2}),
        ('context_exited', {'y': 2}),
        ('context_exited', {'x': 1}),
    ]
