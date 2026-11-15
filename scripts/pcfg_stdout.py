# usage: python pcfg_stdout.py <pcfg_cracker folder> <ruleset> <session name>
import builtins
import contextlib
import os
import runpy
import sys
import threading


# pcfg_guesser stops when stdin is not a terminal; make input() wait forever
def wait_forever(*args):
    threading.Event().wait()
    return ""


pcfg_dir, rules, session = sys.argv[1], sys.argv[2], sys.argv[3]
builtins.input = wait_forever
os.chdir(pcfg_dir)
sys.path.insert(0, pcfg_dir)

# the banner starts with a bare print() to stdout, which would be counted as guess 1
import lib_guesser.banner_info as banner
old_banner = banner.print_banner


def banner_to_stderr():
    with contextlib.redirect_stdout(sys.stderr):
        old_banner()


banner.print_banner = banner_to_stderr

sys.argv = [os.path.join(pcfg_dir, "pcfg_guesser.py"), "-r", rules, "-s", session]
runpy.run_path(sys.argv[0], run_name="__main__")
