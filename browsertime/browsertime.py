import json
import subprocess
import os
import gzip

class browsertime:
    def __init__(self, nsid, url, only_h2=False, firefox=False, timeout=300):
        self.nsid = nsid
        self.url = url
        if firefox:
            assert only_h2
            self.arg = "timeout %d browsertime/do_h2_firefox_prio.sh https://%s/ %s" % (timeout, url, nsid)
        else:
            if only_h2:
                self.arg = "timeout %d browsertime/do_h2_chrome_prio.sh https://%s/ %s" % (timeout, url, nsid)
            else:
                self.arg = "timeout %d browsertime/do_h3_chrome.sh https://%s/ %s %d" % (timeout, url, nsid, timeout * 1000)

    def start(self):
        self.p = subprocess.Popen(self.arg, shell=True, stdout=subprocess.DEVNULL)

    def abort(self):
        self.p.stdout.close()
        self.p.kill()

    def is_running(self):
        poll = self.p.poll()
        return poll == None

    def get(self, filename):
        if filename.endswith(".gz"):
            with gzip.open("/tmp/browsertime-%s/%s" % (self.nsid, filename)) as f:
                return f.read().decode()
        else:
            with open("/tmp/browsertime-%s/%s" % (self.nsid, filename)) as f:
                return f.read()

    def parse(self, filename):
        return json.loads(self.get(filename))
    
    def copy_over(self, todir):
        os.makedirs(todir, exist_ok=True)
        from distutils.dir_util import copy_tree
        copy_tree("/tmp/browsertime-%s" % self.nsid, todir)
