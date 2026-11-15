#!/usr/bin/env python3
"""LIB_XTJSON's check that runs without LiveCode (A-50): xtjson_diff treats values the way LiveCode
does (no types: 1 and 1.0 and "1" are the same, true and "true" are the same).

    python3 -I tests/run_tests.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python'))
import xtjson_diff as xd                    # noqa: E402

CHECKS, FAILS = [0], []


def check(name, ok, got=None):
    CHECKS[0] += 1
    if not ok:
        FAILS.append(name)
        print("FAIL  %s%s" % (name, "" if got is None else "  (got %r)" % (got,)))
    else:
        print("ok    %s" % name)


def done():
    print("\n%d of %d passed" % (CHECKS[0] - len(FAILS), CHECKS[0]))
    return 1 if FAILS else 0


def main():
    check('1 == 1.0 == "1"', xd.same(1, 1.0) and xd.same(1, '1'))
    check('true == "true"', xd.same(True, 'true'))
    check('[255, 0, 0] == "255,0,0"', xd.same([255, 0, 0], '255,0,0'))
    check('"1 " is not 1 (spaces count)', not xd.same('1 ', 1))
    check('different text differs', not xd.same('Hello', 'hello'))
    check('short() cuts long values', len(xd.short('x' * 200, 20)) == 20)
    return done()


if __name__ == '__main__':
    sys.exit(main())
