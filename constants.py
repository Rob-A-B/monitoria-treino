import socket

FORMAT = "utf-8"
HEADER = 32
SERVER = socket.gethostbyname(socket.gethostname())
PORT = 8080
ADDR = (SERVER, PORT)
ACK_TIMEOUT=5.0


ACK = "ACK"
NACK = "NACK"
SYNC = "SYNC"

DISCONNECT_MESSAGE = "sair"
SYNC_MESSAGE = "SYNC"
LOSS_TEST_MESSAGE = "IS THIS LOSS?"
TIMEOUT_TEST_MESSAGE = "TIMEOUT"
# Variáveis de controle de congestionamento

class RecvTimeout(Exception):
    pass