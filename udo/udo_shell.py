from collections import defaultdict, Counter
from enum import Enum
import re

UDO_TOKS = set(['!', '@', '#', '%', '^', '~', '='])

class UDoParser:
    '''
    parse a udo command, FSM style
    '''

    def parse(self, s):
        out = {}
        # ! is handled specially
        importance = s.count('!')
        if importance:
            out['!'] = s.count('!')
            s.translate({'!': ''})

        temp = defaultdict(list)
        state = 'taskname'
        state_level = Counter()
        for c in s:
            if c in UDO_TOKS:
                state = c
                state_level[state] += 1
            else:
                temp[(state, state_level[state])].append(c)

        for k, v in temp.items():
            out[k] = ''.join(v).strip()

        return out

if __name__ == '__main__':
    UDoParser()
