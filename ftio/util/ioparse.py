import sys
from ftio.parse.print import Print

def main(args=sys.argv):
    out = Print(args)
    out.print_json_lines()

if __name__ == "__main__":
    main(sys.argv)
