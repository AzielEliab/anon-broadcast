"""Allow `python -m anon_broadcast` to print the same status as the console script."""

from anon_broadcast.cli import main

raise SystemExit(main())
