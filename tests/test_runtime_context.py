import pytest


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
