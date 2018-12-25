import multiprocessing as mtp
import anytree as tree
import socket
import errno
import time
import rabbit
from anytree.exporter import DotExporter

class RabbitHole(object):

    def __init__(self, root_link, depth=5, processes=1, is_tor=False, minimum_port=3420):
        """Trace all linked articles from the first sentence of any definitions by Wikipedia.

        Args:
          root_link: Valid url of a wikipedia definition page.
          depth: Total number of links to trace.
          processes: Number of Tor connections to open.
          is_tor: Request will be made using anonymous ip addresses (slow).
          minimum_port: Start of port range for Tor connections.
        RaiseError:
          ValueError: Invalid url in root_link.
        Return:
          RabbitHole object.
        """
        self.root_link = root_link
        self.depth = depth
        self.processes = processes
        self.is_tor = is_tor
        self.minimum_port = minimum_port
        self.previous_result = None

    def send_rabbits(self):
        """Starts processes to fetch results from Wikipedia.
        """
        # Manager provides sharing of data structures between processes
        manager = mtp.Manager()
        # `task_queue` is the common job queue for all processes
        task_queue = mtp.JoinableQueue()
        # `result_dict` accumulates results from all processes
        result_dict = manager.dict()

        # Get the topic from the linl
        article = self.root_link.split("/")[-1]
        # Put article in the queue as the starting point, with depth 0
        task_queue.put((article,0))

        # Start number of process requested
        for n in range(self.processes):
            worker = rabbit.Rabbit(task_queue, result_dict, self.depth, self.get_port_pair() if self.is_tor else None)
            worker.start()

        # Wait for job queue to be depleted
        task_queue.join()

        # Combine the result and build the tree
        hat = {article: tree.Node(article)}
        for title in result_dict.keys():
            if title!=article:
                hat[title] = tree.Node(title, parent=hat[result_dict[title]])

        manager.shutdown()
        self.previous_result = hat[article]
        return self.previous_result

    def save_graph(self, path):
        """Save the last fetched result as a dot graph.
        """
        try:
            if self.previous_result:
                DotExporter(self.previous_result).to_picture(path)
            else:
                print("No trace result found, cannot save a graph. Perform a trace first.")
        except Exception as e:
            print(e)

    def get_port_pair(self):
        """Find a pair of ports for Tor connection.

        RaiseError:
          EADDRINUSE: Socket port in use.
        Return:
          A tuple with two port number.
        """
        ports = []
        p = self.minimum_port
        while len(ports) < 2:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind(("127.0.0.1", p))
                ports.append(p)
            except socket.error as e:
                if e.errno == errno.EADDRINUSE:
                    print("Port is already in use, trying next ...")
                    pass
                else:
                    # Something else raised the socket.error exception
                    print(e)
            finally:
                p += 1
            s.close()
        return tuple(ports)
