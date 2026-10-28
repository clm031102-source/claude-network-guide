"""PyInstaller windowed entry point (no console and no elevation)."""
import multiprocessing
import os
import sys


if __name__ == "__main__":
    multiprocessing.freeze_support()
    # Windowed executables have no stdio handles; third-party loggers expect them.
    for name in ("stdin", "stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "r" if name == "stdin" else "w"))
    from app.desktop import main
    raise SystemExit(main())
