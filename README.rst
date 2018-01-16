***************
runtime-context
***************

.. code-block:: shell

    pip install runtime-context


--------------------------
``RuntimeContext`` Example
--------------------------

.. code-block:: python

    from runtime_context import RuntimeContext

    runtime_context = RuntimeContext()


    def do_something(i):
        if runtime_context.dry_run:
            print('{} - dry run'.format(i))
        else:
            print('{} - for real'.format(i))


    with runtime_context(dry_run=False):
        do_something(1)  # for real

        with runtime_context(dry_run=True):
            do_something(2)  # dry run

            runtime_context.dry_run = False
            do_something(3)  # for real

        with runtime_context():
            do_something(4)  # for real

            runtime_context.dry_run = True
            do_something(5)  # dry run

        do_something(6)  # for real


-------------------------------
``runtime_context_env`` Example
-------------------------------

.. code-block:: python

    import json
    from typing import Union  # noqa

    from runtime_context import EnvBase, runtime_context_env  # noqa


    @runtime_context_env
    class YourApp:
        dry_run = False
        db_name = None
        config_file = None


    env = YourApp()  # type: Union[YourApp, EnvBase]


    @env.context_var_set.listener(predicate=lambda name: name == 'config_file')
    def reload_config():
        if not env.config_file:
            return

        print('Reloading config from {}'.format(env.config_file))
        with open(env.config_file) as f:
            config = json.load(f)
            for k, v in config.items():
                env.set(k, v)


    with env():
        assert env.dry_run is False
        assert env.db_name is None

        env.config_file = 'config.json'  # prints 'Reloading config from config.json'

        assert env.db_name == 'products'  # read from config.json file

        with env(dry_run=True):
            assert env.dry_run is True
