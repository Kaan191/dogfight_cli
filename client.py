import json
import logging
import socket
import selectors
from collections import namedtuple
from typing import Dict, Optional


logger = logging.getLogger(__name__)


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

    def receive(self) -> Dict[str, Optional[str]]:

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
                            f'received {recv_data} from connection {data.connid}'
                        )
                    else:
                        logger.debug(
                            f'no data received, closing connection {data.connid}'
                        )
                        sock.close()

                    return json.loads(recv_data.decode('utf-8'))

    def send(self, msg: Dict[str, Optional[str]]) -> None:

        events = self.sel.select(timeout=3)
        if events:
            for key, mask in events:
                if mask & selectors.EVENT_WRITE:
                    sock = key.fileobj
                    data = key.data

                    logger.debug(
                        f'sending {msg} to connection {data.connid}'
                    )
                    send_json = json.dumps(msg).encode('utf-8')
                    sock.send(send_json)  # Should be ready to write

    def close(self):

        events = self.sel.select(timeout=3)
        for key, mask in events:
            if mask & selectors.EVENT_READ:
                sock = key.fileobj
                self.sel.unregister(sock)
                sock.close()
        self.sel.close()
