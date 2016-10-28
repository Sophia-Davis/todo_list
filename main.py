import os.path as osp
import json

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
        #create json file that's an empty list
       with open(TODO_FN, 'w') as f:
           json.dump([], f)
           print("No TODO list found. Making new TODO list")

    with open(TODO_FN, 'r') as f:
        task_list = json.load(f)
        new_task = {'taskname': taskname, 'deadline': deadline, 'description': description}
        task_list.append(new_task)
        task_list = sorted(task_list, key=lambda x: x['deadline'])
    with open(TODO_FN, 'w') as f:
        json.dump(task_list, f)

@clk.command()
def print_tasks():
    with open(TODO_FN, 'r') as f:
        print(json.load(f))

@clk.command()
def remove(task):
    pass

@clk.group()
def main():
    pass

main.add_command(add)
main.add_command(remove)
main.add_command(print_tasks)

if __name__ == '__main__':
    main()
