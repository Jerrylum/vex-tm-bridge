"""
Entry point for running vex-tm-bridge as a module.

This allows the package to be run using:
python -m vex_tm_bridge --tm-host-ip localhost --port 8000
"""

from .web import main

if __name__ == "__main__":
    main()
