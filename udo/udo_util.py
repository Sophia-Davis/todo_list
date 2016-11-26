from datetime import datetime as dtt
import re
import traceback as trc

import click as clk
from dateparser import parse
import pytz


class IntegerSetType(clk.ParamType):
    name = 'set of integers'
    regex = re.compile(r'[0-9]+')

    def convert(self, value, param, ctx):
        try:
            return set([int(x) for x in IntegerSetType.regex.findall(value)])
        except Exception:
            self.fail(trc.format_exc(), param, ctx)


T_INT_SET = IntegerSetType()


def enumerated_prompt(items, head_question, select_question, prefix=''):
    clk.echo(head_question)
    for ix, item in enumerate(items):
        clk.echo('{: 3d}) {}'.format(ix, item))

    return clk.prompt(select_question, type=T_INT_SET)


def aware_now():
    return dtt.now(pytz.utc)


def parse_deadline(dt: str) -> dtt:
    deadline = parse(dt, settings={
        'PREFER_DAY_OF_MONTH': 'first',
        'PREFER_DATES_FROM': 'future',
        'RETURN_AS_TIMEZONE_AWARE': True}
    )
    return deadline
