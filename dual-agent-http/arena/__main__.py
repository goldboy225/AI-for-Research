import argparse
import json
from .config import Config
from .controller import run

def main():
    parser = argparse.ArgumentParser(description='Run a loopback-only synthetic HTTP experiment')
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True, help='New output directory; existing data is never overwritten')
    args = parser.parse_args()
    result = run(Config.load(args.config), args.output)
    print(json.dumps({'aggregate': result['aggregate'], 'adaptation': result['adaptation']}, indent=2))

if __name__ == '__main__':
    main()
