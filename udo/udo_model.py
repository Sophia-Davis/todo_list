from functools import total_ordering
import json
import os.path as osp
import re
import traceback as trc

import click as clk
import marshmallow as mmw


class IntegerSetType(clk.ParamType):
    name = 'set of integers'
    regex = re.compile(r'[0-9]+')

    def convert(self, value, param, ctx):
        try:
            return set([int(x) for x in IntegerSetType.regex.findall(value)])
        except Exception:
            self.fail(trc.format_exc(), param, ctx)


T_INT_SET = IntegerSetType()


@total_ordering
class Task:

    def __init__(self, *, taskname, t_created, description='',
                 deadlines=None, recur_seconds=None,
                 children=None, parents=None, tags=None,
                 importance=0):

        self.taskname = taskname
        self.t_created = t_created
        self.deadlines = deadlines
        self.recur_seconds = recur_seconds
        self.description = description
        self.importance = importance
        self.tags = tags

        self.children = set([] if children is None else children)
        self.parents = set([] if parents is None else parents)

        self._completed = False

    def __lt__(self, other):
        try:
            return min(self.deadlines) > min(other.deadlines)
        # TypeError will be raised if either deadline is None
        except TypeError:
            return self.t_created < other.t_created

    @property
    def completed(self):
        return self._completed

    def complete(self):
        self._completed = True


class TaskDict:
    todo_dir_json = osp.join(osp.expanduser('~'), '.config/udo_task/')
    todo_fn_json = osp.join(todo_dir_json, 'tasks.json')

    storage_formats = ['json']

    line_format = '{0: <50s} {1: <20s}{2: <60s}'
    date_format = '%Y-%m-%d %H:%M:%S'

    def __init__(self, storage='json'):
        self._d = {}
        if storage not in TaskDict.storage_formats:
            raise NotImplementedError('Storage format "{}" not supported'
                                      .format(self.storage))
        self.storage = storage

        self.setup()

    def _setup_json(self):
        if not osp.isfile(TaskDict.todo_fn_json):
            # create json file that's an empty list
            with open(TaskDict.todo_fn_json, 'w') as f:
                json.dump({}, f)
                print("No TODO list found. Making new TODO list")

    def setup(self):
        if self.storage == 'json':
            self._setup_json()

    def _load_json(self):
        '''
        return dictionary of task objects keyed by their names
        '''
        with open(TaskDict.todo_fn_json, 'r') as f:
            try:
                raw_dict = json.load(f)
            except json.decoder.JSONDecodeError:
                # emtpy file -> empty dict
                f.seek(0)
                if not f.read():
                    self._d = {}
                else:
                    # otherwise, ... problem! raise!
                    raise

        schema = TaskSchema(strict=True)
        self._d = {k: schema.load(v).data for k, v in raw_dict.items()}

    def _save_json(self):
        '''
        saves the dictionary of task objects
        '''
        with open(TaskDict.todo_fn_json, 'w') as f:
            schema = TaskSchema(strict=True)
            raw_dict = {k: schema.dump(v).data for k, v in self._d.items()}
            json.dump(raw_dict, f)

    def load(self):
        if self.storage == 'json':
            self._load_json()
        return self

    def save(self):
        if self.storage == 'json':
            self._save_json()

    def print_lines(self, depth=0, **kwargs):
        '''
        Formats the task's contents in a human-readable format, recursing to
        child tasks. Needs task_dict to be able to access children
        '''
        # FIXME: work in progress
        for task in sorted([t for t in self._d.values() if not t.children]):
            out = TaskDict.line_format.format(
                task.taskname,
                # FIXME: doesn't use deadlines list
                ('[due ' + task.deadlines.strftime(Task.date_format) + ']'
                    if task.deadlines is not None else ''),
                (' - ' + task.description
                    if task.description is not None else '')
            )
            # FIXME FIXME FIXME FOR THE LOVE OF GOD FIXME
            # if task.children:
            #     out += '\n'
            # out += '\n'.join([task_dict[c].print_lines(task_dict,
            #                                            echo=False,
            #                                            depth=depth+1)
            #                   for c in task.children])
            # out = '\t' * (depth + 1) + out
            # if echo:
            clk.echo(out, **kwargs)
            # else:
            #     return out

    def add_task(self, task):
        # enforce strict correctness of parent and child lists
        for tn in task.children | task.parents:
            if tn not in self._d.keys():
                raise ValueError(
                    '{} "{}" of task "{}" not known, aborting'
                    .format(('Parent' if tn in task.children else 'Parent'),
                            tn, task)
                )

        self._d[task.taskname] = task
        for tn in task.children:
            self._d[tn].parents.add(tn)
        for tn in task.parents:
            self._d[tn].children.add(tn)

    def del_task(self, tn):
        del self._d[tn]

    def match_tasks(self, query):
        # TODO: make more sophisticated
        # TODO: match on more than name, i.e. dict queries
        '''
        Returns a set of keys in task_dict which match the query.
        '''
        matches = set([tn for tn in self._d.keys() if query in tn])
        return matches


class TaskSchema(mmw.Schema):
    taskname = mmw.fields.Str(required=True)
    importance = mmw.fields.Int(default=0)

    t_created = mmw.fields.DateTime(required=True)
    deadline = mmw.fields.List(mmw.fields.DateTime(allow_none=True))
    recur_seconds = mmw.fields.List(mmw.fields.Int())

    parents = mmw.fields.List(mmw.fields.Str())
    children = mmw.fields.List(mmw.fields.Str())

    description = mmw.fields.Str(allow_none=True)
    tags = mmw.fields.List(mmw.fields.Str())

    @mmw.post_load
    def make_task(self, data):
        # data is a dictionary that contains all parameters
        return Task(**data)
