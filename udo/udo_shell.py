from collections import Counter
from datetime import datetime as dtt
from datetime import timezone
import re

import click as clk
from dateparser import parse

from .udo_model import Task
from .udo_util import enumerated_prompt


class UDoShell:
    '''
    Handles the input of udo commands using a custom shell.
    '''
    # TODO: document shell mini-language

    sym_deadlines = 'deadlines'
    sym_tag = 'tags'
    sym_recur = 'recur_seconds'
    sym_parents = 'parents'
    sym_desc = 'description'

    com_add = ':add'
    com_del = ':del'
    com_list = ':list'
    com_quit = ':quit'
    com_exit = ':exit'

    tok_sym_tab = {'!': None,
              '@': sym_deadlines,
              '#': sym_tag,
              '%': sym_recur,
              '^': sym_parents,
              '=': sym_desc}

    @staticmethod
    def udo_parse(s: str):
        '''
        Reads a stream of udo tokens into a dictionary.
        '''
        # FIXME 
        pass

    def __init__(self, task_dict, start_shell=com_add):
        self.task_dict = task_dict
        self.dispatch = {UDoShell.com_add: self._parse_add,
                         UDoShell.com_del: self._parse_del,
                         UDoShell.com_list: self._parse_list}

        self.prompts = {UDoShell.com_add: clk.style('uDo ADD ', fg='green'),
                        UDoShell.com_del: clk.style('uDo DEL ', fg='red')}

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
            self.task_dict.del_task(matches[0])
            print('Deleted task:', matches[0])
        else:
            to_delete = enumerated_prompt(matches, 'Multiple matches found...',
                                          'Select numbers of tasks to delete')
            for x in to_delete:
                self.task_dict.del_task(matches[x])
                print('Deleted task "{}"'.format(matches[x]))


    def _parse_add(self, s):
        out = {'t_created': dtt.now(timezone.utc)}
        # ! is handled specially
        out['importance'] = s.count('!')
        s = re.sub('!', '', s)

        list_states = [UDoShell.sym_deadlines, UDoShell.sym_recur,
                       UDoShell.sym_tag, UDoShell.sym_parents]
        for ls in list_states:
            out[ls] = []

        buffers = {}
        seen_ss = {}
        single_states = ['taskname', UDoShell.sym_desc]
        for ss in single_states:
            seen_ss[ss] = False
            buffers[ss] = []

        warnings = set()

        # PARSE BLOCK
        state = 'taskname'
        for c in s:
            if c in UDoShell.tok_sym_tab:
                state = UDoShell.tok_sym_tab[c]
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

        for rs in out[UDoShell.sym_recur]:
            rs = int(rs)

        new_parents = []
        for parent in out[UDoShell.sym_parents]:
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
        out[UDoShell.sym_parents] = new_parents

        new_deadlines = []
        for dt in out[UDoShell.sym_deadlines]:
            deadline = parse(dt, settings={
                'PREFER_DAY_OF_MONTH': 'first',
                'PREFER_DATES_FROM': 'future',
                'RETURN_AS_TIMEZONE_AWARE': True}
            )
            new_deadlines.append(deadline)
        out[UDoShell.sym_deadlines] = new_deadlines

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
        while True:

            if not parse_now:
                print('getting prompt')
                s = clk.prompt(self.prompts[self._cur_shell], type=str)
            else:
                print('setting s to parse_now')
                s = parse_now
                parse_now = None

            print('s is "{}"'.format(s))
            print('parse now is "{}"'.format(parse_now))
            coms = s.split(' ')
            com = coms[0].lower()

            if not s or com in [UDoShell.com_exit, UDoShell.com_quit] :
                return

            elif com in self.dispatch.keys():
                print('com is dispatch')
                self._cur_shell = com
                if len(coms) > 1:
                    parse_now = ' '.join(coms[1:])

            elif com in [':done']:
                print('com is done')
                try:
                    complete = ' '.join(coms[1])
                    self.task_dict.complete(complete)
                except IndexError:
                    clk.echo('No task given to complete.')

            elif com == 'list':
                print('com is list')
                try:
                    filt = ' '.join(coms[1:])
                except IndexError:
                    filt = None
                self.task_dict.list_tasks(filt=filt)

            else:
                print('com is fallthrough')
                self.dispatch[self._cur_shell](s)


if __name__ == '__main__':
    u = UDoShell()
    out = u.get_line()
    print(out)
