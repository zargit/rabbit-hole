import multiprocessing as mtp
from bs4 import BeautifulSoup as bs
from stem.process import launch_tor_with_config
from torrequest import TorRequest
import requests
import shutil
import os
import uuid
import time

baseurl = "https://en.wikipedia.org/wiki/{}"

class Rabbit(mtp.Process):

    def __init__(self, task_queue, result_dict, depth=5, ports=None):
        mtp.Process.__init__(self)
        self.task_queue = task_queue
        self.result_dict = result_dict
        self.depth = depth
        self.ports = ports
        # if self.ports:

        print("Rabbit created: {}".format(self.name))

    def run(self):
        if self.ports:
            self.launch_tor()
            self.tor = TorRequest(ctrl_port=self.ports[0], proxy_port=self.ports[1])
            print("Tor connection at {}".format(self.datadir))
        while True:
            try:
                article, level = self.task_queue.get(timeout=5)

                if level < self.depth:
                    next_articles = self.get_articles(article)
                    for item in next_articles:
                            self.task_queue.put((item, level+1))
                            self.result_dict[item] = article # setting the parent
                    # if level+1 == self.depth:
                    #     self.task_queue.put((None, self.depth+1))
                self.task_queue.task_done()
            except Exception as e:
                print(e)
                break
            finally:
                pass
        if self.ports:
            self.tor.close()
            print("Terminating tor at {}".format(self.datadir))
            time.sleep(5)
            shutil.rmtree(self.datadir)

    def launch_tor(self):
        self.datadir = os.path.expanduser("~") + os.sep + uuid.uuid4().hex
        self.tor_process = launch_tor_with_config({'ControlPort': '{}'.format(self.ports[0]), 'SocksPort': '{}'.format(self.ports[1]), 'DataDirectory': '{}'.format(self.datadir)}, take_ownership=True)

    def get_articles(self, parent):
        selectors = ['table.vcard ~ p:nth-of-type(1)', 'table.infobox ~ p:nth-of-type(1)', '#mw-content-text div > p:nth-of-type(2)']
        try:
            if self.ports:
                html = self.tor.get(baseurl.format(parent))
            else:
                html = requests.get(baseurl.format(parent))
            page = bs(html.text, 'html.parser')
            for css in selectors:
                if page.select(css):
                    return self.get_varified_articles(str(page.select(css)[0].encode("utf-8")).split(".")[0])
        except Exception as e:
            print(e)
        return []

    def get_varified_articles(self, html):
        layout = bs(html, 'html.parser')
        articles = []
        for a in layout.select("a"):
            linkparts = a['href'].split("/")
            if "wiki" not in linkparts:
                continue
            keys = self.result_dict.keys()
            if linkparts[-1] not in keys:
                articles.append(linkparts[-1])
        return articles

    def clear_queue(self):
        try:
            while not self.task_queue.empty():
                self.task_queue.get()
                self.task_queue.task_done()
        except Exception as e:
            print(e)
