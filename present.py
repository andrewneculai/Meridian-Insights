"""Small console helpers for the Sprint 1 demos (ASCII only, works in cmd.exe)."""
import os
import sys

AUTO = "--auto" in sys.argv          # no pauses (for rehearsal / screen recording)
WIDTH = 78

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
if os.name == "nt":
    os.system("")                    # enables ANSI colors in Windows 10+ consoles
_COLOR = sys.stdout.isatty() and "--no-color" not in sys.argv


def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def green(t): return _c("32;1", t)
def red(t): return _c("31;1", t)
def cyan(t): return _c("36;1", t)
def dim(t): return _c("2", t)
def bold(t): return _c("1", t)


def banner(title, subtitle=""):
    print()
    print(cyan("=" * WIDTH))
    print(cyan(f"  {title}"))
    if subtitle:
        print(f"  {subtitle}")
    print(cyan("=" * WIDTH))


def step(n, title):
    print()
    print(cyan(f"--- STEP {n}: {title} " + "-" * max(0, WIDTH - 12 - len(title))))


def say(text="", indent=2):
    for line in str(text).splitlines() or [""]:
        print(" " * indent + line)


def note(text):
    say(dim("> " + text))


def pause(prompt="Press Enter for the next step..."):
    if AUTO:
        return
    try:
        input("\n  " + dim(prompt))
    except EOFError:
        pass


def table(headers, rows, aligns=None, indent=2):
    """Plain-text table. rows: list of lists of str. aligns: string like 'lrrr'."""
    aligns = aligns or "l" * len(headers)
    widths = [max(len(str(h)), *(len(_strip(str(r[i]))) for r in rows)) if rows else len(str(h))
              for i, h in enumerate(headers)]

    def fmt(cells):
        out = []
        for i, c in enumerate(cells):
            pad = widths[i] - len(_strip(str(c)))
            out.append(str(c) + " " * pad if aligns[i] == "l" else " " * pad + str(c))
        return " " * indent + "  ".join(out)

    print(bold(fmt(headers)))
    print(" " * indent + "  ".join("-" * w for w in widths))
    for r in rows:
        print(fmt(r))


def _strip(s):
    import re
    return re.sub(r"\033\[[0-9;]*m", "", s)


def passfail(ok):
    return green("PASS") if ok else red("FAIL")


def imports_of(path):
    """Top-level modules a Python file imports (proves layer separation)."""
    import ast
    tree = ast.parse(open(path, encoding="utf-8").read())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module.split(".")[0])
    mods.discard("__future__")
    return sorted(mods)


def run_pytest(test_path):
    import subprocess
    cmd = [sys.executable, "-B", "-m", "pytest", "-v", "--no-header", "-p", "no:cacheprovider",
           "--color=no", test_path]
    return subprocess.call(cmd)


def part(number, title, presenter, covers):
    """Big section header that makes it obvious whose turn it is."""
    print()
    print()
    print(cyan("#" * WIDTH))
    print(cyan(f"#  PART {number}: {title}"))
    print(cyan(f"#  Presenter: {presenter}"))
    print(cyan("#" * WIDTH))
    for c in covers:
        say("  [x] " + c)


def handoff(from_who, to_who, what):
    print()
    print(bold("*" * WIDTH))
    print(bold(f"*  HANDOFF:  {from_who}  -->  {to_who}"))
    print(bold("*  " + what))
    print(bold("*" * WIDTH))
