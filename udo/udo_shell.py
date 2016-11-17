from collections import defaultdict, Counter
from datetime import datetime as dtt

from .model import Task, match_tasks
from .udo_util import enumerate_prompt


class UDoShell:
    '''
    Handles the input of udo commands using a custom shell.
    '''
    # TODO: document shell mini-language

    TOKENS = set(['!', '@', '#', '%', '^', '='])
    PROMPT = 'uDo > '

    def __init__(self, task_dict):
        self.task_dict = task_dict

    def parse(self, s):
        '''
        Parses a string into a dictionary of udo commands
        '''
        out = {'created': dtt.now()}
        # ! is handled specially
        importance = s.count('!')
        if importance:
            out['importance'] = s.count('!')
            s.translate({'!': ''})

        temp = defaultdict(list)
        state = 'taskname'
        state_level = Counter()
        for c in s:
            if c in UDoShell.TOKENS:
                state = c
                state_level[state] += 1
            else:
                temp[(state, state_level[state])].append(c)

        for k, v in temp.items():
            out[k] = ''.join(v).strip()

        return out

    def mk_task(self, pdict):
        description = None
        recurs = []
        tags = []
        parents = []

        warnings = []

        for k, v in pdict.items():
            if k[0] == '@':
                due_dates.append(v)
            elif k[0] == '#':
                tags.append(v)
            elif k[0] == '%':
                recurs.append(int(v))
            elif k[0] == '=':
                if description is not None:
                    warnings.append('More than one description given!')
                description = v
            elif k[0] == '^':
                par_matches = match_tasks(v, self.task_dict)
                if len(par_matches == 0):
                    warnings.append('No parents found matching "{}"'
                                    .format(v))
                elif len(par_matches > 1):
                    ixes = enumerate_prompt(
                        par_matches,
                        'More than one parent matches "{}"'.format(v),
                        'Please select intended parents.')
                    parents += [par_matches(ix) for ix in ixes]
                else:
                    parents += [par_matches[0]]

        task = Task(**pdict)

    def get_line(self):
        '''
        Run the udo shell.
        '''
        s = input(UDoShell.PROMPT)
        return self.parse(s)


if __name__ == '__main__':
    u = UDoShell()
    out = u.get_line()
    print(out)
