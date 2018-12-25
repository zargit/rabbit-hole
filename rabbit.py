import multiprocessing as mtp
from bs4 import BeautifulSoup as bs
from stem import process
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
        #     self.datadir = os.path.expanduser("~") + os.sep + uuid.uuid4().hex
        #     self.tor = process.launch_tor_with_config({'ControlPort': '{}'.format(ports[0]), 'SocksPort': '{}'.format(ports[1]), 'DataDirectory': '{}'.format(self.datadir)})

        print("Rabbit created: {}".format(self.name))

    def run(self):
        while True:
            try:
                article, level = self.task_queue.get()

                if level < self.depth:
                    next_articles = self.get_articles(article)
                    for item in next_articles:
                            self.task_queue.put((item, level+1))
                            self.result_dict[item] = article # setting the parent

            except Exception as e:
                print(e)
            finally:
                self.task_queue.task_done()
                if level >= self.depth:
                    self.clear_queue()
                    break

    def get_articles(self, parent):
        selectors = ['table.vcard ~ p:nth-of-type(1)', 'table.infobox ~ p:nth-of-type(1)', '#mw-content-text div > p:nth-of-type(2)']
        try:
            page = bs(requests.get(baseurl.format(parent)).text, 'html.parser')
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
