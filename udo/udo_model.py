from functools import total_ordering
import json
import os
import os.path as osp
from typing import List

import click as clk
import marshmallow as mmw

from .udo_util import aware_now, enumerated_prompt


# TODO: make configurable
DUE_DATE_FORMAT = '%a, %b %d, %H:%M'


class TaskSchema(mmw.Schema):

    @classmethod
    def get_fields(cls):
        return cls().fields

    class Meta:
        strict = True

    taskname = mmw.fields.Str(required=True, sh_is_default=True)
    t_created = mmw.fields.DateTime(required=True, sh_init=aware_now)

    importance = mmw.fields.Int(default=0, sh_sym='!', sh_count=True)

    deadlines = mmw.fields.List(mmw.fields.DateTime(), sh_sym='@')
    recur_seconds = mmw.fields.List(mmw.fields.Int(), sh_sym='%')

    parents = mmw.fields.List(mmw.fields.Str(), sh_sym='^')
    children = mmw.fields.List(mmw.fields.Str(), sh_ignore=True)

    description = mmw.fields.Str(default='', sh_sym='=')
    tags = mmw.fields.List(mmw.fields.Str(), sh_sym='#')

    completed = mmw.fields.Bool(default=False, sh_ignore=True)

    @mmw.post_load
    def make_task(self, data):
        return Task(**data)

    @mmw.validates_schema
    def validate(self, task) -> None:
        for key in task.keys():
            if key not in self.fields.keys():
                raise mmw.ValidationError('invalid key {}')

        task_dict = self.context.get('task_dict', False)
        if not task_dict:
            return

        name = task['taskname']
        pair = ('parents', 'children')
        for u, v in [pair] + [pair[::-1]]:
            for t_u in task[u]:
                if t_u not in task_dict:
                    raise mmw.ValidationError(
                        'task "{}" has unknown {} "{}"'
                        .format(name, u[:-1], t_u)
                    )
                elif t_u not in getattr(task_dict[t_u], v):
                    raise mmw.ValidationError(
                        'task "{}"\'s {} "{}" severed'
                        .format(name, u[:-1], t_u)
                    )


@total_ordering
class Task:

    # importance name due desc tags
    short_format = '{: >3s} {: <25s}  {: <25s}  {: >20s}'

    def __init__(self, *, taskname, t_created=None,
                 importance=0, deadlines=None, recur_seconds=None,
                 parents=None, children=None, description='', tags=None,
                 completed=False):

        self.taskname = taskname
        self.t_created = t_created or aware_now()

        self.importance = importance
        self.deadlines = deadlines or set()
        self.recur_seconds = recur_seconds or set()

        self.parents = parents or set()
        self.children = children or set()
        self.tags = tags or set()

        self.description = description

        self.completed = completed

    def __lt__(self, other):
        try:
            return min(self.deadlines) > min(other.deadlines)
        # TypeError will be raised if either deadline is None
        except (ValueError, TypeError):
            return self.t_created < other.t_created

    def format_short(self):
        imp_color = {0: 'white', 1: 'yellow',
                     2: 'organge', 3: 'red'}[self.importance]
        imp_str = clk.style('!' * min(3, self.importance), fg=imp_color)

        due_str = ('' if not self.deadlines
                   else '@ ' + self.deadlines[0].strftime(DUE_DATE_FORMAT))
        tag_str = ('#' if self.tags else '') + ' #'.join(self.tags)

        return Task.short_format.format(
            imp_str, self.taskname, due_str, tag_str
        )


class TaskDict:
    todo_dir_json = osp.join(osp.expanduser('~'), '.config/udo_task/')
    todo_fn_json = osp.join(todo_dir_json, 'tasks.json')

    storage_formats = ['json']

    def __init__(self, storage='json'):
        self._d = {}
        if storage not in TaskDict.storage_formats:
            raise NotImplementedError('Storage format "{}" not supported'
                                      .format(self.storage))
        self.storage = storage

        self.setup()

    def _setup_json(self):
        os.makedirs(TaskDict.todo_dir_json, exist_ok=True)
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
                    return
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

    def list_tasks(self, filt=None, depth=0, **kwargs):
        '''
        Formats the task's contents in a human-readable format, recursing to
        child tasks. Needs task_dict to be able to access children
        '''
        # FIXME: work in progress
        # FIXME: implement filter
        out = []
        for task in sorted([t for t in self._d.values() if not t.parents]):
            out.append(task.format_short())
        clk.echo('\n'.join(out), **kwargs)

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

    def match_tasks(self, query_dict):
        # TODO: make more sophisticated
        '''
        Returns a set of keys in task_dict which match the query.
        '''
        # FIXME: match on more than name, i.e. dict queries
        query = query_dict['taskname']
        return sorted([tn for tn in self._d.keys() if query in tn])

    def reconcile_relative(self, name: str, relative='parent') -> List[str]:
        par_matches = self.match_tasks({'taskname': name})

        l = len(par_matches)
        if l == 0:
            clk.echo('No {} found matching "{}"'.format(relative, name))
        elif l > 1:
            ixes = enumerated_prompt(
                par_matches,
                'More than one of the {0} matches "{}"'.format(relative, name),
                'Please select intended {0}.'
            )
            return [par_matches(ix) for ix in ixes]
        else:
            return par_matches

    def __contains__(self, key):
        return key in self._d

    def __getitem__(self, key):
        return self._d[key]
