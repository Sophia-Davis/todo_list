from functools import partial
import re

import click as clk
from dateparser import parse
import marshmallow as mmw

from .udo_model import Task, TaskSchema
from .udo_util import enumerated_prompt, parse_deadline

PROMPT = partial(clk.prompt, prompt_suffix='')
CONFIRM = partial(clk.confirm, prompt_suffix='')


class UDoShell:
    '''
    Handles the input of udo commands using a custom shell.
    '''
    # TODO: document shell mini-language

    com_add, com_del = 'add', 'del'
    com_list, com_ls = 'list', 'ls'
    com_quit, com_exit = 'quit', 'exit'
    com_done = 'done'
    com_mod = 'mod'

    field_info = TaskSchema.get_fields()
    sh_syms = {
        f.metadata['sh_sym']: name for name, f in field_info.items()
        if 'sh_sym' in f.metadata
    }

    def sh_parse(self, s):  # noqa
        '''
        Reads a stream of udo tokens into a dictionary.
        '''

        out = {}
        state = None
        for k, f in UDoShell.field_info.items():
            if 'sh_count' in f.metadata:
                out[k] = s.count(f.metadata['sh_sym'])
                s = re.sub(f.metadata['sh_sym'], '', s)
                continue
            if 'sh_is_default' in f.metadata:
                assert state is None
                state = k
            if 'sh_init' in f.metadata:
                out[k] = f.metadata['sh_init']()
            elif 'sh_sym' in f.metadata:
                out[k] = []

        assert state is not None

        out[state].append('')
        for c in s:
            if c in UDoShell.sh_syms.keys():
                state = UDoShell.sh_syms[c]
                out[state].append('')
            else:
                out[state][-1] = out[state][-1] + c

        for k, f in UDoShell.field_info.items():
            if 'sh_init' in f.metadata or 'sh_count' in f.metadata:
                continue
            # TODO: better way of handling "reentrant options"
            elif not isinstance(f, mmw.fields.List) and out[k]:
                if out[k][1:]:
                    clk.echo('Multiple entries for "{}", taking the first'
                             .format(k))
                out[k] = out[k][0]

        for relation in ['parents', 'children']:
            new = []
            for name in out[relation]:
                new += self.task_dict.reconcile_relative(name,
                                                         relative=relation)
            out[relation] = new

        new = []
        for deadline in out['deadlines']:
            new.append(parse_deadline(deadline))
        out['deadlines'] = new
        
        print(out)
        return out

    def __init__(self, task_dict, start_shell=com_add):
        self.task_dict = task_dict
        self.dispatch = {UDoShell.com_add: self._parse_add,
                         UDoShell.com_del: self._parse_del}

        self.prompts = {UDoShell.com_add: clk.style('uDo ADD > ', fg='green'),
                        UDoShell.com_del: clk.style('uDo DEL > ', fg='red')}

        self._cur_shell = start_shell
        self._task_schema = TaskSchema()
        self._task_schema.context['task_dict'] = task_dict

    def parse_fail(self, msg, repeat=True):
        clk.echo(msg, color='red')
        if repeat:
            self.read_task()

    # TODO: del by other than name
    def _parse_del(self, s: str):
        out = self.sh_parse(s)

        matches = self.task_dict.match_tasks(out)
        l = len(matches)

        if l == 0:
            clk.echo('No matches. No tasks deleted.')
        elif l == 1:
            self.task_dict.del_task(matches[0])
            clk.echo('Deleted task "{}"'.format(matches[0]))
        else:
            to_delete = enumerated_prompt(matches, 'Multiple matches found...',
                                          'Select numbers of tasks to delete')
            for x in to_delete:
                self.task_dict.del_task(matches[x])
            clk.echo('Deleted {} tasks'.format(len(to_delete)))

    def _parse_add(self, s: str):
        out = self.sh_parse(s)

        # match parents
        # TODO: move to TaskDict method

        if len(out['taskname']) < 5:
            save = CONFIRM('You may have meant a command. Save anyway?')
        else:
            save = True

        if save:
            task = Task(**out)
            self.task_dict.add_task(task)

    def _parse_list(self, s: str):
        out = self.sh_parse(s)

        self.task_dict.list_tasks(filt=out)

    def read_task(self, parse_now=None):  # noqa
        # TODO: unify data model to be DRYer, less magicky
        '''
        Parses a string into a task.

        Args:
            parse_now: input to parse immediately, skipping the input step
        '''
        while True:

            if not parse_now:
                s = PROMPT(self.prompts[self._cur_shell], type=str)
            else:
                s = parse_now
                parse_now = None

            coms = s.split(' ')
            com = coms[0].lower()

            if not s or com in [UDoShell.com_exit, UDoShell.com_quit]:
                return

            elif com in self.dispatch.keys():
                self._cur_shell = com
                if len(coms) > 1:
                    parse_now = ' '.join(coms[1:])

            elif com in [UDoShell.com_done]:
                try:
                    complete = ' '.join(coms[1])
                    self.task_dict.complete(complete)
                except IndexError:
                    clk.echo('No task given to complete.')

            elif com in [UDoShell.com_list, UDoShell.com_ls]:
                try:
                    filt_dict = self.sh_parse(' '.join(coms[1:]))
                except IndexError:
                    filt_dict = None
                self.task_dict.list_tasks(filt=filt_dict)

            else:
                self.dispatch[self._cur_shell](s)
