import socket, threading
import pickle

def SendMessage(uname):
    while True:
        MsDict={}
        msg = input('\nMe > ')
        MsDict['uname'] = uname
        MsDict['msg'] = msg
        # print (f'MyDiict {str(MsDict)}')
        data = pickle.dumps (MsDict, -1)
        cli_sock.send(data)

def ReceiveMessage():
    while True:
        data_loaded = pickle.loads(cli_sock.recv(1024))
        uname = data_loaded.get('uname')
        msg = data_loaded.get ('msg')
        print(f'\n{uname}> {msg}')

if __name__ == "__main__":
    # socket
    cli_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # connect
    HOST = 'localhost'
    PORT = 5021
    cli_sock.connect((HOST, PORT))
    print('Connected to remote host...')
    uname = input('Enter your name to enter the chat > ')
    print (f'Hello {uname}!')
    cli_sock.send(uname.encode())

    thread_send = threading.Thread(target = SendMessage, args=[uname])
    thread_send.start()

    thread_receive = threading.Thread(target = ReceiveMessage)
    thread_receive.start()