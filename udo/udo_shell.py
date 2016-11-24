from collections import Counter
from datetime import datetime as dtt

import click as clk
from dateparser import parse

from .udo_model import Task
from .udo_util import enumerated_prompt


class UDoShell:
    '''
    Handles the input of udo commands using a custom shell.
    '''
    # TODO: document shell mini-language

    TOKENS = {'!': None,
              '@': 'deadlines',
              '#': 'tags',
              '%': 'recur_seconds',
              '^': 'parents',
              '=': 'description'}

    def __init__(self, task_dict, start_shell='add'):
        self.task_dict = task_dict
        self.dispatch = {'add': self._parse_add,
                         'del': self._parse_del}
        self.prompts = {'add': 'uDo ADD ',
                        'del': clk.style('uDo DEL ', fg='red')}

        self._cur_shell = start_shell

    def parse_fail(self, msg, repeat=True):
        clk.echo(msg, color='red')
        if repeat:
            self.read_task()

    # TODO: del by other than name
    def _parse_del(self, s):
        matches = sorted(self.task_dict.match_tasks(s))
        if len(matches) == 0:
            print('No matches. No tasks deleted.')
        elif len(matches) == 1:
            del self.task_dict[matches[0]]
            print('Deleted task:', matches[0])
        else:
            to_delete = enumerated_prompt(matches, 'Multiple matches found...',
                                          'Select numbers of tasks to delete')
            for x in to_delete:
                self.task_dict.del_task(matches[x])
                print('Deleted task "{}"'.format(matches[x]))

    def _parse_add(self, s):
        out = {'t_created': dtt.now()}
        # ! is handled specially
        out['importance'] = s.count('!')
        s.translate({'!': ''})

        list_states = ['deadlines', 'recur_seconds', 'tags', 'parents']
        for ls in list_states:
            out[ls] = []

        buffers = {}
        seen_ss = {}
        single_states = ['taskname', 'description']
        for ss in single_states:
            seen_ss[ss] = False
            buffers[ss] = []

        warnings = set()

        # PARSE BLOCK
        state = 'taskname'
        for c in s:
            if c in UDoShell.TOKENS:
                state = UDoShell.TOKENS[c]
                if state in list_states:
                    out[state].append([])
                else:
                    if seen_ss[state]:
                        warnings.add("More than one {} given! Using last."
                                     .format(state))
                        buffers[state] = []
                    else:
                        seen_ss[state] = True
            else:
                if state in list_states:
                    out[state][-1].append(c)
                elif state in single_states:
                    buffers[state].append(c)

        # POSTPROCESS BLOCK
        for ls in list_states:
            out[ls] = [''.join(chars).strip() for chars in out[ls]]
        for ss in single_states:
            out[ss] = ''.join(buffers[ss]).strip()

        if not buffers['taskname']:
            return self.parse_fail('Taskname cannot be empty!')

        for rs in out['recur_seconds']:
            rs = int(rs)

        new_parents = []
        for parent in out['parents']:
            par_matches = match_tasks(self.task_dict, parent)
            print(par_matches)
            if len(par_matches) == 0:
                warnings.add('No parents found matching "{}"'.format(parent))
            elif len(par_matches) > 1:
                ixes = enumerated_prompt(
                    par_matches,
                    'More than one parent matches "{}"'.format(parent),
                    'Please select intended parents.'
                )
                new_parents += [par_matches(ix) for ix in ixes]
            else:
                new_parents += [par_matches.pop()]
        out['parents'] = new_parents

        new_deadlines = []
        for dt in out['deadlines']:
            deadline = parse(dt, settings={
                'PREFER_DAY_OF_MONTH': 'first',
                'PREFER_DATES_FROM': 'future',
                'RETURN_AS_TIMEZONE_AWARE': True}
            )
            new_deadlines.append(deadline)
        out['deadlines'] = new_deadlines

        task = Task(**out)
        for warning in warnings:
            clk.echo(message=clk.style(warning, fg='red'))

        self.task_dict.add_task(task)

    def read_task(self, parse_now=None):  # noqa
        # TODO: unify data model to be DRYer, less magicky
        '''
        Parses a string into a task.

        Args:
            parse_now: input to parse immediately, skipping the input step
        '''
        if parse_now is None:
            s = clk.prompt(self.prompts[self._cur_shell], type=str)
        else:
            s = parse_now

        if not s:
            return
        elif s.lower() in self.dispatch.keys():
            self._cur_shell = s.lower()
        elif s.lower() == 'list':
            self.task_dict.print_lines()
        else:
            self.dispatch[self._cur_shell](s)
        self.read_task()


if __name__ == '__main__':
    u = UDoShell()
    out = u.get_line()
    print(out)
