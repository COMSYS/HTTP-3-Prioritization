import gzip
import json
import os
import subprocess

from learning import LEARNING_BASE_DIR
from testbed import BROWSERTIME_DIR, LIGHTHOUSE_DIR


class Docker:
    def __init__(self, nsid, url, timeout=300, lighthouse=True):
        self.nsid = nsid
        self.url = url
        self.lighthouse = lighthouse
        if lighthouse:
            self.arg = (
                f"timeout {timeout} {LIGHTHOUSE_DIR}/run.sh https://{url}/ {nsid}"
            )
        else:
            self.arg = f"timeout {timeout} {BROWSERTIME_DIR}/do_h3_chrome.sh https://{url}/ {nsid} {timeout * 1000} {LEARNING_BASE_DIR/ 'script.js'}"

    def start(self):
        self.p = subprocess.Popen(self.arg, shell=True, stdout=subprocess.DEVNULL)

    def abort(self):
        self.p.stdout.close()
        self.p.kill()

    def is_running(self):
        poll = self.p.poll()
        return poll == None

    def get(self, filename):
        if self.lighthouse:
            with open(f"/tmp/lighthouse-{self.nsid}/{filename}") as f:
                return f.read()
        elif filename.endswith(".gz"):
            with gzip.open(f"/tmp/browsertime-{self.nsid}/{filename}") as f:
                return f.read().decode()
        else:
            with open(f"/tmp/browsertime-{self.nsid}/{filename}") as f:
                return f.read()

    def parse(self, filename):
        return json.loads(self.get(filename))

    def copy_over(self, todir):
        os.makedirs(todir, exist_ok=True)
        from distutils.dir_util import copy_tree

        if self.lighthouse:
            copy_tree(f"/tmp/lighthouse-{self.nsid}", todir)
        else:
            copy_tree(f"/tmp/browsertime-{self.nsid}", todir)
