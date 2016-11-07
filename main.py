#! /usr/bin/python
from datetime import datetime as dtt
from functools import total_ordering
import json
import os.path as osp
import traceback as trc

import click as clk
from dateparser import parse
import marshmallow as mmw

# DISPLAY; ADD ITEMS; DELETE ITEMS
# TODO: allow date display format configuration

TODO_FN = osp.join(osp.expanduser('~'), '.config/to_do.json')


@total_ordering
class Task:
    line_format = '{0: <20s} {1: <20s}{2: <60s}'
    date_format = '%Y-%m-%d %H:%M:%S'

    def __init__(self, taskname=None, t_created=None,
                 deadline=None, description='',
                 children=None, parents=None):

        if taskname is None:
            raise ValueError('need to provide a task name!')
        if t_created is None:
            raise ValueError('need to provide a creation date!')
        self.taskname = taskname
        self.t_created = t_created
        self.deadline = deadline
        self.description = description

        self.children = set([] if children is None else children)
        self.parents = set([] if parents is None else parents)

    def print_lines(self, task_dict, echo=True, depth=0, **kwargs):
        '''
        Formats the task's contents in a human-readable format, recursing to
        child tasks. Needs task_dict to be able to access children
        '''
        out = Task.line_format.format(
            self.taskname,
            ('[due ' + self.deadline.strftime(Task.date_format) + ']'
                if self.deadline is not None else ''),
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

    def __lt__(self, other):
        if self.deadline is None:
            return True
        if other.deadline is None:
            return False
        else:
            return self.deadline < other.deadline


class TaskSchema(mmw.Schema):
    taskname = mmw.fields.Str(required=True)
    t_created = mmw.fields.DateTime(required=True)
    deadline = mmw.fields.DateTime(allow_none=True)
    description = mmw.fields.Str(allow_none=True)

    parents = mmw.fields.List(mmw.fields.Str())
    children = mmw.fields.List(mmw.fields.Str())

    @mmw.post_load
    def make_task(self, data):
        # data is a dictionary that contains all parameters
        return Task(**data)


def load_tasks():
    '''
    return dictionary of task objects keyed by their names
    '''
    with open(TODO_FN, 'r') as f:
        raw_dict = json.load(f)
    schema = TaskSchema(strict=True)
    return {k: schema.load(v).data for k, v in raw_dict.items()}


def save_tasks(task_dict):
    '''
    saves the dictionary of task objects
    '''
    with open(TODO_FN, 'w') as f:
        schema = TaskSchema(strict=True)
        raw_dict = {k: schema.dump(v).data for k, v in task_dict.items()}
        json.dump(raw_dict, f)


def match_tasks(task_dict, query):
    # TODO: make more sophisticated
    '''
    Returns a set of keys in task_dict which match the query.
    '''
    matches = set([tn for tn in task_dict.keys() if query in tn])
    return matches


@clk.command()
@clk.argument('task', nargs=-1)
@clk.option('--deadline', '-d')
@clk.option('--desc', '-s')
@clk.option('--parent', '-p')
def add(task, deadline=None, desc='', parent=''):
    # TODO: parse arguments, define syntax, add to help
    taskname = ' '.join(task)
    if not osp.isfile(TODO_FN):
        # create json file that's an empty list
        with open(TODO_FN, 'w') as f:
            json.dump({}, f)
            print("No TODO list found. Making new TODO list")

    task_dict = load_tasks()
    if deadline is not None:
        try:
            # TODO: assume smarter default times; "tomorrow" -> 5 AM tomorrow
            # suboptimal
            format_date = parse(deadline, settings={
                'PREFER_DAY_OF_MONTH': 'first',
                'PREFER_DATES_FROM': 'future',
                'RETURN_AS_TIMEZONE_AWARE': True})
        except Exception:
            # TODO: not in final version
            trc.print_exc()
            print('Unable to decipher input. Try another format.')
            return
    else:
        format_date = None

    parent_tns = match_tasks(task_dict, parent)
    new_task = Task(taskname, dtt.now(),
                    deadline=format_date,
                    description=desc, parents=parent_tns)
    for ptn in parent_tns:
        task_dict[ptn].children.add(taskname)

    task_dict[taskname] = new_task
    save_tasks(task_dict)

# read and write from todo list


@clk.command('list')
@clk.option('--sort', '-s', type=str)
def task_list(sort=None):
    task_dict = load_tasks()
    if sort == 'name':
        sorted_tasks = sorted(task_dict.values(), key=lambda x: x.taskname)
    # sort by date by default
    else:
        sorted_tasks = sorted(task_dict.values())
    clk.echo(clk.style('TODO LIST:', bold=True))
    for task in sorted_tasks:
        task.print_lines(task_dict)


@clk.command()
@clk.argument('query', nargs=1)
def remove(query):
    '''immediately delete unique matches; ask for confirmation if multiple
    matches are found '''
    with open(TODO_FN, 'r') as f:
        task_dict = json.load(f)

    matches = sorted(match_tasks(task_dict, query))
    if len(matches) == 0:
        print('No matches. No tasks deleted.')
    elif len(matches) == 1:
        del task_dict[matches[0]]
        print('Deleted task:', matches[0])
    else:
        print('Multiple matches found.')
        for a, b in enumerate(matches):
            print('{}: "{}"'.format(a, b))
        to_delete = input('Type the numbers of the tasks you want deleted:')
        try:
            nums = [int(x) for x in to_delete.split(' ')]
# TODO= make criteria more forgiving allow separation by , or ", "
        except Exception:
            print('Input Error : invalid input.')
            return
        for x in nums:
            del task_dict[matches[x]]
            print('Deleted task', matches[x])

    with open(TODO_FN, 'w') as f:
        json.dump(task_dict, f)


@clk.group()
def main():
    pass


main.add_command(add)
main.add_command(remove)
main.add_command(task_list)

if __name__ == '__main__':
    main()
