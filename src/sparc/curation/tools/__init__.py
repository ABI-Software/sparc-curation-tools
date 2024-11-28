import os
import kaleido

from importlib import reload

__version__ = "0.7.7"

if kaleido.__version__ == "0.2.1":
    kaleido_dir = os.path.dirname(os.path.abspath(kaleido.__file__))
    base_file = os.path.join(kaleido_dir, 'scopes', 'base.py')
    with open(base_file) as f:
        contents = f.readlines()

    line = contents[187]
    if 'setDaemon(True)' in line:
        line = line.replace('setDaemon(True)', 'daemon = True')
        contents[187] = line

        with open(base_file, 'w') as f:
            f.write(''.join(contents))

        kaleido = reload(kaleido)
