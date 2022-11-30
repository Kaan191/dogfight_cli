import json
import sys
import socket
import selectors
import types

sel = selectors.DefaultSelector()

host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((host, port))
lsock.listen()
print(f"Listening on {(host, port)}")
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

DATA_BUFFER = {'sent_to': []}


def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, outb={})
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


def service_connection(key, mask):
    global DATA_BUFFER

    sock = key.fileobj
    data = key.data
    # print(f'data: {DATA_BUFFER}')
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            try:
                recv_json = json.loads(recv_data.decode('utf-8'))
                recv_key = list(recv_json.keys())[0]
                if recv_key not in data.outb:
                    DATA_BUFFER.update(recv_json)
            except json.JSONDecodeError:
                pass
        else:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if DATA_BUFFER and len(DATA_BUFFER) == 3:
            if data.addr not in DATA_BUFFER['sent_to']:
                only_data = {k: v for k, v in DATA_BUFFER.items() if k != 'sent_to'}
                print(f"Echoing {only_data} to {data.addr}")
                send_json = json.dumps(only_data).encode('utf-8')
                sock.send(send_json)  # Should be ready to write
                DATA_BUFFER['sent_to'].append(data.addr)
            if len(DATA_BUFFER['sent_to']) == 2:
                DATA_BUFFER = {'sent_to': []}


# the event loop
try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            # accept new connections
            if key.data is None:
                accept_wrapper(key.fileobj)
            # service connection
            else:
                service_connection(key, mask)
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()
