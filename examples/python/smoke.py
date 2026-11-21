import json
import sys
from client import KEY_ERROR, run

if __name__ == '__main__':
    try:
        print(json.dumps(run(sys.argv[1] if len(sys.argv) > 1 else 'stack')))
    except Exception as error:
        print(KEY_ERROR if str(error) == KEY_ERROR else 'Example failed', file=sys.stderr)
        sys.exit(1)
