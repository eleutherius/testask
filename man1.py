import socket, time
from threading import Thread
from multiprocessing import Process, Queue

host = "127.0.0.1"
port = 8080
def client():
    print ('client')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    # print(s.recv(1024).decode('utf8'))

    while True:
        buf = input()
        s.send(buf.encode('utf8'))
        result = s.recv(1024)
        print('Ответ сервера: ', result.decode('utf8'))
        if buf == "exit":
            break
    s.close()

    time.sleep(10)


def server():
    print ('server')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(5)
    sock, addr = s.accept()
    print("client connected with address " + addr[0])
    sock.send(b"hello!")
    while True:
      buf = sock.recv(1024)
      buf = buf.rstrip()
      if buf.decode('utf8') == "exit":
        sock.send(b"bye")
        break
      elif buf:
        sock.send(buf)
        print(buf.decode('utf8'))
    sock.close()
q = Queue()

process_one = Process(target=server())
process_two = Process(target=client())

process_one.start()
process_two.start()

q.close()
q.join_thread()

process_one.join()
process_two.join()
