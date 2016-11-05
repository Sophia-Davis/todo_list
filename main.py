import json
import os.path as osp
from pprint import pprint as pp

import click as clk

# DISPLAY; ADD ITEMS; DELETE ITEMS

TODO_FN = osp.join(osp.expanduser('~'), '.config/to_do.json')


class Task:

    def __init__(self, taskname, deadline, description):
        self.taskname = taskname
        self.deadline = deadline
        self.description = description

    def to_dict(self):
        return {'taskname': self.taskname,
                'deadline': self.deadline,
                'description': self.description}


@clk.command()
@clk.argument('taskname', nargs=1)
@clk.argument('deadline', nargs=1)
@clk.argument('description', nargs=1)
def add(taskname, deadline, description):
    if not osp.isfile(TODO_FN):
        # create json file that's an empty list
        with open(TODO_FN, 'w') as f:
            json.dump({}, f)
            print("No TODO list found. Making new TODO list")

    with open(TODO_FN, 'r') as f:
        task_dict = json.load(f)
        new_task = {'deadline': deadline, 'description': description}
        task_dict[taskname] = new_task
    with open(TODO_FN, 'w') as f:
        json.dump(task_dict, f)


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
        print('Deleted task', matches[0])
    else:
        print('Multiple matches found.')
        for a, b in enumerate(matches):
            print('{}: "{}"'.format(a, b))
        to_delete = input('Type the numbers of the tasks you want deleted:')
        try:
            nums = [int(x) for x in to_delete.split(' ')]
#TODO= make criteria more forgiving allow separation by , or ", "
        except Exception:
            print('Error: invalid input.')
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
