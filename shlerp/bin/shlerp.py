#!/usr/bin/env python3
import sys
import platform

def main():
    # Check OS compatibility
    if platform.system() not in ["Darwin", "Linux"]:
        print("This package only supports macOS and Linux/Unix systems.")
        sys.exit(1)

    # Parse arguments
    args = sys.argv[1:]  # Exclude script name
    if "-u" in args or "--upload" in args:
        print("The upload function is disabled due to API changes.")
        sys.exit(0)

    # Replace `-h` with `--help` in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == "-h":
            sys.argv[i] = "--help"

    # Import and call the main function from shlerp.main
    from shlerp.main import main as shlerp_main
    shlerp_main()

if __name__ == "__main__":
    main()
