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
