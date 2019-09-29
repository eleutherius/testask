import socket, threading
import pickle
import traceback

def accept_client():
    while True:
        #accept
        cli_sock, cli_add = ser_sock.accept()
        msg  = cli_sock.recv (1024)
        data_loaded = pickle.loads (cli_sock.recv (1024))
        # print (f'data_loaded {data_loaded}')
        uname = data_loaded.get ('uname')


        CONNECTION_LIST.append((uname, cli_sock))
        print(f'{uname} is now connected')
        thread_client = threading.Thread(target = broadcast_usr, args=[msg, cli_sock])
        thread_client.start()

def broadcast_usr(uname, cli_sock):
    while True:
        try:
            data = cli_sock.recv(1024)
            if data:
                data_loaded = pickle.loads (data)
                print (f'{data_loaded.get("uname")} spoke')
                b_usr(cli_sock, data)
        except Exception:
            print (traceback.format_exc ( ))
            exit(1)

def b_usr(cs_sock, msg):
    for client in CONNECTION_LIST:
        if client[1] != cs_sock:
            client[1].send(msg)
            print ("message was send")
            # client[1].send(msg)

if __name__ == "__main__":
    CONNECTION_LIST = []

    # socket
    ser_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # ser_sock.setsockopt (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # bind
    HOST = 'localhost'
    PORT = 5021
    try:
        ser_sock.bind((HOST, PORT))
    except:
        print (f'Port - {PORT} is already in use')
        PORT = int (input ("Input another port number:"))
        try:
            ser_sock.bind((HOST, PORT))
        except:
            print (f"Port - {PORT} already  used too!!!")
            exit (1)
    # listen
    ser_sock.listen(1)
    print(f'Chat server started on port : {PORT}')

    thread_ac = threading.Thread(target = accept_client)
    thread_ac.start()
