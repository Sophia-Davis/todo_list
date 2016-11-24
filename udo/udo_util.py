import click as clk

from .udo_model import T_INT_SET


def enumerated_prompt(items, head_question, select_question, prefix=''):
    clk.echo(head_question)
    for ix, item in enumerate(items):
        clk.echo('{: 3d}) {}'.format(ix, item))

    return clk.prompt(select_question, type=T_INT_SET)
