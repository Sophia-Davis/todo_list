#! /usr/bin/python
from datetime import datetime as dtt
import json
import os.path as osp
from pprint import pprint as pp
import datetime
import time
import traceback as trc

import click as clk
from dateparser import parse
import marshmallow as mmw

# DISPLAY; ADD ITEMS; DELETE ITEMS

TODO_FN = osp.join(osp.expanduser('~'), '.config/to_do.json')


class Task:

    def __init__(self, taskname='task', t_created=None,
                 deadline=None, description=''):
        self.taskname = taskname
        self.t_created = t_created
        self.deadline = deadline
        self.description = description

    def to_dict(self):
        return {'taskname': self.taskname,
                'deadline': self.deadline,
                'description': self.description}


class TaskSchema(mmw.Schema):
    taskname = mmw.fields.Str()
    t_created = mmw.fields.DateTime()
    deadline = mmw.fields.DateTime()
    description = mmw.fields.Str()

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
    schema = TaskSchema()
    return {k: schema.load(v).data for k, v in raw_dict.items()}


def save_tasks(task_dict):
    '''
    saves the dictionary of task objects
    '''
    with open(TODO_FN, 'w') as f:
        schema = TaskSchema()
        raw_dict = {k: schema.dump(v).data for k, v in task_dict.items()}
        json.dump(raw_dict, f)


@clk.command()
@clk.argument('task', nargs=-1)
@clk.option('--deadline', '-d')
@clk.option('--desc', '-s')
def add(task, deadline=None, desc=''):
    taskname = ' '.join(task)
    if not osp.isfile(TODO_FN):
        # create json file that's an empty list
        with open(TODO_FN, 'w') as f:
            json.dump({}, f)
            print("No TODO list found. Making new TODO list")

    task_dict = load_tasks()
    if deadline is not None:
        try:
            format_date = parse(deadline, settings={
                'PREFER_DAY_OF_MONTH': 'first',
                'PREFER_DATES_FROM': 'future',
                'RETURN_AS_TIMEZONE_AWARE': True})
        except Exception:
            trc.print_exc()
            print('Unable to decipher input. Try another format.')
            return
    else:
        format_date = None

    new_task = Task(taskname, dtt.now(),
                    deadline=format_date,
                    description=desc)

    task_dict[taskname] = new_task
    save_tasks(task_dict)

# read and write from todo list


@clk.command()
def print_tasks():
    with open(TODO_FN, 'r') as f:
        pp(json.load(f))


@clk.command()
@clk.argument('query', nargs=1)
def remove(query):
    '''immediately delete unique matches; ask for confirmation if multiple
    matches are found '''
    with open(TODO_FN, 'r') as f:
        task_dict = json.load(f)

    matches = sorted([task for task in task_dict.keys() if query in task])
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
main.add_command(print_tasks)

if __name__ == '__main__':
    main()
