#! /usr/bin/python
import click as clk

from udo.udo_shell import UDoShell
from udo.udo_model import TaskDict
# DISPLAY; ADD ITEMS; DELETE ITEMS
# TODO: allow date display format configuration


def shell(shell=UDoShell.com_add, parse_now=None):
    # TODO: storage methods, etc, through config
    task_dict = TaskDict().load()
    u = UDoShell(task_dict, start_shell=shell)
    try:
        u.read_task(parse_now=parse_now)
    finally:
        task_dict.save()


@clk.command()
def add():
    # TODO: parse arguments, define syntax, add to help
    shell(shell=UDoShell.com_add)


@clk.command('del')
def delete():
    shell(shell=UDoShell.com_del)


@clk.command('list')
@clk.option('--sort', '-s', type=str)
def task_list(sort=None):
    task_dict = TaskDict().load()
    task_dict.print_lines(sort)


@clk.group(invoke_without_command=True)
@clk.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        add()


main.add_command(add)
main.add_command(delete)
main.add_command(task_list)

if __name__ == '__main__':
    main()
