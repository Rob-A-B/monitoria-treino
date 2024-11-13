import select
import socket
import threading
import time

from constants import *
from hashing import *

def flush_socket(conn):
    conn.setblocking(0)
    while True:
        inputready, _, _ = select.select([conn], [], [], 0.0)
        if len(inputready)==0: break
        for s in inputready: s.recv(1)
    conn.setblocking(1)

def send_message(conn, msg, sequence):
    message = str(msg).encode(FORMAT)
    header = '\n'.join([str(len(msg)), str(sequence)]).encode(FORMAT)
    header += b' ' * (HEADER - len(header))
    conn.send((header + message))

def handle_client(conn, addr, id_cliente):
    print(f'[NEW CONNECTION] {addr} - Id Cliente: {id_cliente} connected.')
    received_ids = set()  # Conjunto para armazenar os IDs de mensagens recebidas
    next_expected_id = 0  # Próximo ID de mensagem esperado

    try:
        while True:
            header_data = conn.recv(HEADER).decode(FORMAT)
            header_fields = header_data.split('\n')

            if header_data == '':
                print("Received empty packet assuming connection is closed")
                break

            if len(header_fields) != 3:
                print(f"[ERROR] Invalid header received from {addr}")
                send_message(conn, "Invalid header received", 0)
                flush_socket(conn)
                continue

            msg_len, msg_id, checksum = header_fields
            msg_id = int(msg_id.strip())

            if int(msg_len) + int(msg_id) + int(checksum) != 0:
                print(f'[ERROR] Integrity error in message from {addr}')
                send_message(conn, NACK, msg_id)
                flush_socket(conn)
                continue

            if msg_id in received_ids:
                print(f'[INFO] Duplicated package detected for message {msg_id} from {addr}')
                send_message(conn, ACK, msg_id)  # Envia ACK para pacotes duplicados
                flush_socket(conn)
                continue

            # Adiciona o ID recebido ao conjunto de IDs recebidos
            received_ids.add(msg_id)
            msg_bytes = conn.recv(int(msg_len))
            msg = msg_bytes[:-32].decode(FORMAT)

            print(f'[{addr}] ({msg_id}) {msg}')

            if not verifying_hash(msg_bytes):
                print('[ERROR] Hash failed')
                send_message(conn, NACK, msg_id)
            else:
                # Verifica se o ID da mensagem é o próximo esperado
                if msg_id == next_expected_id:
                    print(f'[INFO] Received expected message {msg_id}')
                    send_message(conn, ACK, msg_id)
                    next_expected_id += 1  # Incrementa o próximo ID esperado
                else:
                    print(f'[INFO] Out-of-order message {msg_id} received, waiting for message {next_expected_id}')
                    send_message(conn, ACK, msg_id)  # Confirma pacotes fora de ordem

            if msg == DISCONNECT_MESSAGE:
                print(f"[DISCONNECT] {addr} sent disconnect message")
                break

    except ConnectionResetError:
        print(f'[ERROR] Connection reset by {addr}')

    conn.close()


if __name__ == '__main__':
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.settimeout(1)
    server.listen()
    num_clients = 0
    print(f'[LISTENING] Server is listening on {SERVER}')
    try:
        while True:
            try:
                conn, addr = server.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr,num_clients), daemon=True)
                thread.start()
                print(f'[ACTIVE CONNECTIONS] {threading.active_count() - 1}')
                num_clients+=1
            except socket.timeout:
                pass
    except KeyboardInterrupt:
        print("Server shutting down")
        server.close()