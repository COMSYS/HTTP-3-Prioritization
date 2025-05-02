import logging
import os
from subprocess import PIPE, Popen
from threading import Lock, Thread

from learning import LEARNING_BASE_DIR

logger = logging.getLogger("process")
logger.setLevel(logging.INFO)
logger.propagate = False
if not (LEARNING_BASE_DIR / "run_data").exists():
    (LEARNING_BASE_DIR / "run_data").mkdir(parents=True, exist_ok=True)
handler = logging.FileHandler(
    LEARNING_BASE_DIR / "run_data" / "current_run_process.log", "w"
)
with open(LEARNING_BASE_DIR / "run_data" / "current_run_process.log", "w"):
    pass  # clears log file
formatter = logging.Formatter("[%(asctime)s-%(name)s-%(levelname)s]: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class ownprocess:
    def __init__(
        self, args, namespace=None, cwd=None, print_f=print, additionalargs=None
    ):
        if namespace is not None:
            args = ["ip", "netns", "exec", namespace] + args
        self.args = args
        self.cwd = cwd
        self.print_f = print_f
        self.waskilled = False
        self.lock = Lock()
        self.additionalargs = additionalargs

    def get(self, filename):
        if self.cwd is None:
            return None
        with open(self.cwd + "/" + filename) as f:
            return f.read()

    def copy_over(self, dir):
        if self.cwd is None:
            return False
        os.makedirs(dir, exist_ok=True)
        from distutils.dir_util import copy_tree

        copy_tree(self.cwd, dir)
        return True

    def get_additionalargs(self):
        return self.additionalargs

    def run(self, exceptionok=False):
        process = Popen(self.args, cwd=self.cwd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        if not exceptionok:
            assert process.returncode == 0, (stdout, stderr)

    def check_stdout(self):
        for line in self.p.stdout:
            self.print_f("stdout %s %s" % (str(self.args), line))

    def check_stderr(self):
        for line in self.p.stderr:
            self.print_f("stderr %s %s" % (str(self.args), line))
        with self.lock:
            if not self.waskilled:
                poll = self.p.poll()
                assert poll != None, (self.waskilled, poll)
                assert poll == 0, (self.waskilled, poll)

    def run_bg(self):
        self.p = Popen(self.args, cwd=self.cwd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        self.threads = [
            Thread(target=self.check_stderr),
            Thread(target=self.check_stdout),
        ]
        for t in self.threads:
            t.start()

    def willbekilled(self):
        with self.lock:
            self.waskilled = True

    def kill(self):
        self.willbekilled()
        self.p.kill()
        self.p.stdout.close()
        self.p.stderr.close()


def run(
    args, namespace=None, cwd=None, exceptionok=False, bg=False, additionalargs=None
):
    op = ownprocess(
        args, namespace, cwd, print_f=logger.info, additionalargs=additionalargs
    )
    if bg:
        op.run_bg()
    else:
        op.run(exceptionok)
    return op
