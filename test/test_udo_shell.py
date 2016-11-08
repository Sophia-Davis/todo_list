import string
import time

import numpy as np
import numpy.random as npr
import pytest

from udo.udo_shell import UDO_TOKS, UDoParser


def test_udo_parser_endurance():
    up = UDoParser()
    seqs = [[' '], list(string.ascii_letters), list(string.printable)]
    for i in range(5000):
        l = 50 + int(100 * npr.random())
        p = npr.choice(np.asarray([0, 1, 2]), size=l, p=[0.1, 0.7, 0.2])
        s = ''.join([npr.choice(seqs[p[ix]]) for ix in range(l)])

        print(s)
        up.parse(s)


def test_udo_parser_basic():
    up = UDoParser()

    assert not up.parse('')

    out = up.parse('test task')
    print(out)
    assert out.pop(('taskname', 0)) == 'test task'
    assert not out

    out = up.parse('test task three @ tomorrow')
    print(out)
    assert out.pop(('taskname', 0)) == 'test task three'
    assert out.pop(('@', 1)) == 'tomorrow'

    out = up.parse('test task four @ tomorrow @ tomorrow')
    print(out)
    assert out.pop(('@', 1)) == 'tomorrow'
    assert out.pop(('@', 2)) == 'tomorrow'

    out = up.parse('test task four @ tomorrow @ tomorrow !!! %3d #house')
    print(out)
    assert out['!'] == 3
    assert out[('%', 1)] == '3d'
