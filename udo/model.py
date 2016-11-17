from functools import total_ordering
import re
import traceback as trc

import click as clk
import marshmallow as mmw


class IntegerSetType(clk.ParamType):
    name = 'set of integers'
    regex = re.compile('r[0-9]+[^0-9]')

    def convert(self, value, param, ctx):
        try:
            return set([int(x) for x in IntegerSetType.regex.findall(value)])
        except Exception:
            self.fail(trc.format_exc(), param, ctx)

T_INT_SET = IntegerSetType()


class Task:
    line_format = '{0: <20s} {1: <20s}{2: <60s}'
    date_format = '%Y-%m-%d %H:%M:%S'

    def __init__(self, *, taskname, t_created, description='',
                 deadlines=None, recur_seconds=None,
                 children=None, parents=None,
                 importance=0):

        self.taskname = taskname
        self.t_created = t_created
        self.deadlines = deadlines
        self.recur_seconds = recur_seconds
        self.description = description
        self.importance = importance

        self.children = set([] if children is None else children)
        self.parents = set([] if parents is None else parents)

    def print_lines(self, task_dict, echo=True, depth=0, **kwargs):
        '''
        Formats the task's contents in a human-readable format, recursing to
        child tasks. Needs task_dict to be able to access children
        '''
        out = Task.line_format.format(
            self.taskname,
            ('[due ' + self.deadlines.strftime(Task.date_format) + ']'
                if self.deadlines is not None else ''),
            (' - ' + self.description if self.description is not None else '')
        )
        if self.children:
            out += '\n'
        out += '\n'.join([task_dict[c].print_lines(task_dict,
                                                   echo=False,
                                                   depth=depth+1)
                          for c in self.children])
        out = '\t' * (depth + 1) + out
        if echo:
            clk.echo(out, **kwargs)
        else:
            return out

    @total_ordering
deadlines
deadlines

class TaskSchema(mmw.Schema):
    taskname = mmw.fields.Str(required=True)
    t_created = mmw.fields.DateTime(required=True)
    deadline = mmw.fields.List(mmw.fields.DateTime(allow_none=True))
    recur_seconds = mmw.fields.Int(allow_none=True)
    description = mmw.fields.Str(allow_none=True)
    importance = mmw.fields.Int(default=0)

    parents = mmw.fields.List(mmw.fields.Str())
    children = mmw.fields.List(mmw.fields.Str())

    @mmw.post_load
    def make_task(self, data):
        # data is a dictionary that contains all parameters
        return Task(**data)
    

def match_tasks(task_dict, query):
    # TODO: make more sophisticated
    '''
    Returns a set of keys in task_dict which match the query.
    '''
    matches = set([tn for tn in task_dict.keys() if query in tn])
    return matches
