"""Enable ``python -m sanctioned`` to run the matching demo."""

from __future__ import annotations

import sys

from sanctioned.cli import main

if __name__ == "__main__":
    sys.exit(main())
