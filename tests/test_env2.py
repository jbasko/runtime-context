import pytest

from runtime_context.env2 import runtime_context_env


def test_all():
    @runtime_context_env
    class App:
        x = 0
        y = 1

        def __init__(self):
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
