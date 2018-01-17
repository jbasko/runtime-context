import pytest

from runtime_context import Context, RuntimeContextWrapper


def test_rc_basics(rc):
    """
    Basics are:
        * calling creates a context manager
        * nested contexts inherit values from contexts above
        * unknown attributes raise AttributeError
    """

    with rc(a=1):
        assert rc.a == 1
        with pytest.raises(AttributeError):
            assert not rc.b

        with rc(b=2):
            assert (rc.a, rc.b) == (1, 2)

            with rc():
                assert (rc.a, rc.b) == (1, 2)

                with rc(a=4):
                    assert (rc.a, rc.b) == (4, 2)

                    with rc(a=5, b=5):
                        assert (rc.a, rc.b) == (5, 5)

                    assert (rc.a, rc.b) == (4, 2)

                assert (rc.a, rc.b) == (1, 2)

            assert (rc.a, rc.b) == (1, 2)

        assert rc.a == 1
        with pytest.raises(AttributeError):
            assert not rc.b


def test_rc_is_context_var_and_get(rc):
    assert not rc.is_context_var('xx')
    assert rc.get('xx') is None
    assert rc.get('xx', 5) == 5

    with rc(xx=False):
        assert rc.is_context_var('xx')
        assert rc.get('xx') is False
        assert rc.get('xx', 5) is False

        with rc():
            assert rc.is_context_var('xx')
            assert rc.get('xx') is False
            assert rc.get('xx', 5) is False

            with rc():
                assert rc.is_context_var('xx')
                assert rc.get('xx') is False
                assert rc.get('xx', 5) is False

                with rc(xx=True):
                    assert rc.is_context_var('xx')
                    assert rc.get('xx') is True
                    assert rc.get('xx', 5) is True

        assert rc.is_context_var('xx')
        assert rc.get('xx') is False
        assert rc.get('xx', 5) is False

    assert not rc.is_context_var('xx')
    assert rc.get('xx') is None
    assert rc.get('xx', 5) == 5


def test_rc_set(rc):
    with rc():
        assert not rc.is_context_var('yy')
        assert rc.get('yy') is None
        assert rc.get('yy', 5) == 5

        with rc():
            assert not rc.is_context_var('yy')

            rc.set('yy', False)
            assert rc.is_context_var('yy')
            assert rc.get('yy') is False
            assert rc.get('yy', 5) is False

        assert rc.get('yy') is None
        assert rc.get('yy', 5) == 5

        with rc():
            rc.set('yy', True)

            with rc():
                assert rc.is_context_var('yy')
                assert rc.get('yy') is True

                with rc():
                    rc.set('yy', 22)
                    assert rc.is_context_var('yy')
                    assert rc.get('yy') == 22

                assert rc.is_context_var('yy')
                assert rc.get('yy') is True

            assert rc.is_context_var('yy')
            assert rc.get('yy') is True

        assert not rc.is_context_var('yy')


@pytest.mark.parametrize('reset_method', ['do_reset', 'do_delete'])
def test_rc_reset(rc, reset_method):
    def do_reset():
        rc.reset('xxx')

    def do_delete():
        del rc.xxx

    reset = locals()[reset_method]

    with rc(xxx=None):
        assert rc.xxx is None

        reset()
        with pytest.raises(AttributeError):
            _ = rc.xxx  # noqa

        with rc(xxx=1):
            assert rc.xxx == 1

            reset()
            with pytest.raises(AttributeError):
                _ = rc.xxx  # noqa

            rc.xxx = 2
            reset()
            with pytest.raises(AttributeError):
                _ = rc.xxx  # noqa

            rc.xxx = 3

        with pytest.raises(AttributeError):
            _ = rc.xxx  # noqa

        with pytest.raises(AttributeError):
            _ = rc.xxx  # noqa


def test_can_reset_nonexistent_context_var_with_reset_method(rc: RuntimeContextWrapper):
    assert 'xxx' not in rc._stack[-1]
    rc.reset('xxx')
    rc.reset('xxx')


def test_cannot_reset_nonexistent_context_var_via_del_attr(rc: RuntimeContextWrapper):
    # As we don't keep a list of all names, if something
    # is not in the context we don't know if it's a context var
    # so we delegate to object.__delattr__ and that obviously raises AttributeError.

    with pytest.raises(AttributeError):
        del rc.xxx

    with pytest.raises(AttributeError):
        del rc.xxx


def test_context_entered_and_exited_events_are_triggered(rc):
    calls = []

    @rc.context_entered.listener
    def context_entered(context_vars):
        calls.append(('context_entered', context_vars))

    @rc.context_exited.listener
    def context_existed(context_vars):
        calls.append(('context_exited', context_vars))

    assert len(calls) == 0

    with rc():
        assert len(calls) == 1
        assert calls[-1] == ('context_entered', {})

        with rc(x=1, y=2):
            assert len(calls) == 2
            assert calls[-1] == ('context_entered', {'x': 1, 'y': 2})

            rc.set('x', 1000)

        assert len(calls) == 3
        assert calls[-1] == ('context_exited', {'x': 1000, 'y': 2})

    assert len(calls) == 4
    assert calls[-1] == ('context_exited', {})


def test_setting_attribute_on_runtime_context_updates_current_context_vars(rc):
    with rc():
        assert rc._stack[-1] == {}

        rc.x = 1
        rc.y = 2
        assert rc._stack[-1] == {'x': 1, 'y': 2}

        with rc(w=0):
            assert rc._stack[-1] == {'w': 0}
            rc.z = 3
            assert rc._stack[-1] == {'w': 0, 'z': 3}

        assert rc._stack[-1] == {'x': 1, 'y': 2}


def test_reset_context(rc):
    with rc():
        assert rc._stack[-1] == {}

        rc.reset_context()
        assert rc._stack[-1] == {}

        rc.x = 1
        rc.y = 2

        rc.reset_context()
        assert rc._stack[-1] == {}

        with rc(x=11, y=22):
            rc.x = 111
            rc.reset_context()
            assert rc._stack[-1] == {}


def test_push_and_pop_context_and_current_context(rc):
    rc.x = 55

    rc.push_context()
    assert len(rc._stack) == 2
    assert rc.x == 55
    assert rc.current == {}

    rc.pop_context()
    assert len(rc._stack) == 1
    assert rc.x == 55
    assert rc.current == {'x': 55}

    rc.push_context({'x': 8888, 'y': 9999})
    assert rc.x == 8888
    assert rc.current == {'x': 8888, 'y': 9999}

    rc.pop_context()
    assert rc.x == 55
    assert rc.current == {'x': 55}


def test_there_is_always_one_context_already_pushed_on_wrapper_creation():
    wrapper1 = RuntimeContextWrapper()
    assert len(wrapper1._stack) == 1
    assert isinstance(wrapper1.current, Context)

    wrapper2 = RuntimeContextWrapper()
    assert len(wrapper2._stack) == 1
    assert wrapper1._stack is not wrapper2._stack
    assert wrapper1.current is not wrapper2.current
