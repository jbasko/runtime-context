import pytest


def test_can_import_runtime_context():
    from runtime_context import RuntimeContext, RuntimeContextEnv  # noqa


def test_rc_fixture(rc):
    import runtime_context

    assert isinstance(rc, runtime_context.RuntimeContext)
    assert len(rc._stack) == 1
    assert rc._stack[-1] == {}


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


def test_rc_has_and_get(rc):
    assert not rc.has('xx')
    assert rc.get('xx') is None
    assert rc.get('xx', 5) == 5

    with rc(xx=False):
        assert rc.has('xx')
        assert rc.get('xx') is False
        assert rc.get('xx', 5) is False

        with rc():
            assert rc.has('xx')
            assert rc.get('xx') is False
            assert rc.get('xx', 5) is False

            with rc():
                assert rc.has('xx')
                assert rc.get('xx') is False
                assert rc.get('xx', 5) is False

                with rc(xx=True):
                    assert rc.has('xx')
                    assert rc.get('xx') is True
                    assert rc.get('xx', 5) is True

        assert rc.has('xx')
        assert rc.get('xx') is False
        assert rc.get('xx', 5) is False

    assert not rc.has('xx')
    assert rc.get('xx') is None
    assert rc.get('xx', 5) == 5


def test_rc_set(rc):
    with rc():
        assert not rc.has('yy')
        assert rc.get('yy') is None
        assert rc.get('yy', 5) == 5

        with rc():
            assert not rc.has('yy')

            rc.set('yy', False)
            assert rc.has('yy')
            assert rc.get('yy') is False
            assert rc.get('yy', 5) is False

        assert rc.get('yy') is None
        assert rc.get('yy', 5) == 5

        with rc():
            rc.set('yy', True)

            with rc():
                assert rc.has('yy')
                assert rc.get('yy') is True

                with rc():
                    rc.set('yy', 22)
                    assert rc.has('yy')
                    assert rc.get('yy') == 22

                assert rc.has('yy')
                assert rc.get('yy') is True

            assert rc.has('yy')
            assert rc.get('yy') is True

        assert not rc.has('yy')
