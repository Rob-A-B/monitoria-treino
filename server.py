import socket
from constants import *
from hashing import verifying_hash

def send_message(conn, msg, sequence):
    header = '\n'.join([str(len(msg)), str(sequence)]).encode(FORMAT)
    header += b' ' * (HEADER - len(header))
    message = header + msg.encode(FORMAT)
    conn.send(message)

def handle_client(conn, addr, id_cliente):
    print(f'[NEW CONNECTION] {addr} - Id Cliente: {id_cliente} connected.')
    received_ids = set()

    try:
        while True:
            header_data = conn.recv(HEADER).decode(FORMAT)
            if not header_data:
                print("[INFO] Connection closed by client")
                break

            header_fields = header_data.split('\n')
            if len(header_fields) != 3:
                print(f"[ERROR] Invalid header from {addr}")
                send_message(conn, "Invalid header received", 0)
                continue

            msg_len, msg_id, checksum = header_fields
            msg_id = int(msg_id.strip())
            msg_len = int(msg_len.strip())
            checksum = int(checksum.strip())

            # Verificação de integridade (checksum)
            if (msg_len + msg_id + checksum) != 0:
                print(f"[ERROR] Checksum error detected for message ID {msg_id} from {addr}")
                send_message(conn, NACK, msg_id)
                continue

            # Recebe a mensagem
            msg_bytes = conn.recv(msg_len)
            msg = msg_bytes[:-32].decode(FORMAT)

            # Verificação de hash
            if not verifying_hash(msg_bytes):
                print(f"[ERROR] Hash verification failed for message ID {msg_id} from {addr}")
                send_message(conn, NACK, msg_id)
                continue

            # Detecção de pacotes duplicados
            if msg_id in received_ids:
                print(f"[INFO] Duplicate message ID {msg_id} detected from {addr}")
                send_message(conn, ACK, msg_id)
                continue

            received_ids.add(msg_id)
            print(f'[{addr}] ({msg_id}) {msg}')
            send_message(conn, ACK, msg_id)

            if msg == DISCONNECT_MESSAGE:
                print(f"[DISCONNECT] {addr} sent disconnect message")
                break

    except ConnectionResetError:
        print(f"[ERROR] Connection reset by {addr}")

    conn.close()

if __name__ == '__main__':
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen()
    print(f'[LISTENING] Server is listening on {SERVER}')

    while True:
        conn, addr = server.accept()
        id_cliente = 1  # Exemplo de atribuição de ID
        handle_client(conn, addr, id_cliente)
