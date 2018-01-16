"""
Demonstrates how to create a RuntimeContext-aware application environment instance
that you can use as a singleton from anywhere.
"""

import json
from typing import Union  # noqa

from runtime_context import EnvBase, runtime_context_env  # noqa


@runtime_context_env
class YourApp:
    dry_run = False
    db_name = None
    config_file = None


env = YourApp()  # type: Union[YourApp, EnvBase]


@env.context_var_updated.listener(predicate=lambda name: name == 'config_file')
def reload_config():
    if not env.config_file:
        # env.reset_context()
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
