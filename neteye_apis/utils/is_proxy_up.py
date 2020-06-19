
import socket

def is_proxy_up(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        s.connect((ip, port))
        s.close()
        return True
    except:
        return False