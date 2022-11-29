import logging
import pathlib
import socket
import selectors
from collections import namedtuple


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(
    pathlib.Path(__file__).resolve().parent / 'client.log'
)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
formatter.datefmt = '%Y-%m-%d:%H:%M:%S'
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)


SocketData = namedtuple(
    'SocketData',
    'connid msg_total recv_total messages outb'
)


class Client():

    def __init__(self, connid, host: str, port: int):

        self.sel = selectors.DefaultSelector()

        # make socket
        server_addr = (host, int(port))
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(server_addr)

        # events to accept
        events = selectors.EVENT_READ | selectors.EVENT_WRITE

        # initialise data block to track state of socket
        data = SocketData(
            connid=connid,
            msg_total=0,
            recv_total=0,
            messages=[],
            outb=b''
        )
        self.sel.register(sock, events, data=data)

    def receive(self):

        recv_data = None

        events = self.sel.select(timeout=3)
        if events:
            for key, mask in events:
                if mask & selectors.EVENT_READ:
                    sock = key.fileobj
                    data = key.data
                    recv_data = sock.recv(1024)

                    if recv_data:
                        logger.debug(
                            f'received data from connection {data.connid}'
                        )
                    if not recv_data:
                        logger.debug(
                            f'no data received, closing connection {data.connid}'
                        )
                        sock.close()

                    # no guarantee all data is collected...fix this
                    return recv_data

    def send(self, msg: bytes):

        events = self.sel.select(timeout=3)
        if events:
            for key, mask in events:
                if mask & selectors.EVENT_WRITE:
                    sock = key.fileobj
                    data = key.data

                    while True:
                        if msg:
                            logger.debug(
                                f'sending {msg} to connection {data.connid}'
                            )
                            sent = sock.send(msg)
                            msg = msg[sent:]
                        else:
                            logger.debug(f'message sent to {data.connid}')
                            break

    def close(self):

        events = self.sel.select(timeout=3)
        for key, mask in events:
            if mask & selectors.EVENT_READ:
                sock = key.fileobj
                self.sel.unregister(sock)
                sock.close()
        self.sel.close()
