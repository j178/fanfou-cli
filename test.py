import os
import sys

print('sys',sys.stdin.isatty())
print('os',os.isatty(sys.stdin.fileno()))
