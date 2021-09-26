import opcode
import dis

a = 3


def foo(x):
    return a


dis.dis(foo)
