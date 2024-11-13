import select
import socket
import time
from hashing import *
from constants import *

# Variáveis de controle de congestionamento
cwnd = 1  # Congestion window inicial
ssthresh = 16  # Limite inicial para Slow Start

def receive_timeout(conn, size):
    conn.setblocking(0)
    ready = select.select([conn], [], [], ACK_TIMEOUT)
    if ready[0]:
        conn.setblocking(1)
        return client.recv(size).decode(FORMAT)
    else:
        conn.setblocking(1)
        raise RecvTimeout

def receive(client, current_sequence):
    try:
        header_data = receive_timeout(client, HEADER)
        header_fields = header_data.split('\n')
        msg_length, msg_id = header_fields
        msg_id = int(msg_id.strip())

        if msg_length:
            msg_length = int(msg_length.strip())
            msg = receive_timeout(client, msg_length)
            if msg.startswith(f"{SYNC}-"):
                return int(msg.split(f"{SYNC}-", 1)[-1])  # Retorna o ID do cliente na sincronização
            print(f"RECEIVED RESPONSE FROM SERVER {msg}")
            return msg_id  # Retorna o ID da mensagem para ACKs normais

    except RecvTimeout:
        print("[ERROR] Timeout while waiting for response")
        return None
    except ValueError as e:
        print(f"[ERROR] Value error: {e}")
        return None


    if msg_id != current_sequence:
        print(f"Ignoring ACK for message with sequence {msg_id}. We probably already retransmitted and received an ack for this message")
        msg_length = int(msg_length.strip())
        receive_timeout(client, msg_length)
        return receive(client, current_sequence)

    if msg_length:
        msg_length = int(msg_length.strip())
        msg = receive_timeout(client, msg_length)
        if msg.startswith(f"{SYNC}-"):
            return int(msg.split(f"{SYNC}-", 1)[-1])
        print(f"RECEIVED RESPONSE FROM SERVER {msg}")

def send(client, msg, identifier, insert_error, insert_error_hash, retransmit_attempts=3):
    try:
        content = str(msg).encode(FORMAT)

        if insert_error_hash:
            content += b'0000'
        else:
            content = add_hash(content)

        checksum = (len(content) + identifier) * (1 if insert_error else -1)
        header = '\n'.join([str(len(content)), str(identifier), str(checksum)]).encode(FORMAT)
        header += b' ' * (HEADER - len(header))
        message = (header + content)
        client.send(message)
    except BrokenPipeError:
        print("[ERROR] conexão quebrada")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        if retransmit_attempts:
            return send(client, msg, identifier, insert_error, insert_error_hash, retransmit_attempts=retransmit_attempts-1)

def send_window_tahoe(client, messages, start_sequence):
    global cwnd, ssthresh
    idx = 0  # Índice do início da janela

    while idx < len(messages):
        # Determina quantos pacotes podem ser enviados com base no valor de cwnd
        end_idx = idx + int(cwnd)  # Limita o tamanho da janela de envio
        window = messages[idx:end_idx]

        print(f"Enviando janela: {window}")  # Imprime a janela atual
        for message in window:
            send(client, message, start_sequence, False, False)
            start_sequence += 1

        # Aguarda ACKs e ajusta cwnd de acordo
        acks_received = 0
        for _ in range(len(window)):
            try:
                ack_id = receive(client, start_sequence - len(window) + acks_received)
                print(f"ACK received for sequence {ack_id}")
                acks_received += 1

            except RecvTimeout:
                print("Timeout detected, entering Slow Start")
                ssthresh = max(cwnd // 2, 1)
                cwnd = 1  # Reinicia a janela de congestionamento
                start_sequence -= len(window) - acks_received  # Reajusta a sequência
                idx -= len(window) - acks_received  # Reajusta o índice para retransmissão
                break

        # Ajuste de cwnd após receber ACKs
        if acks_received == len(window):
            if cwnd < ssthresh:
                cwnd *= 2  # Crescimento exponencial em Slow Start
            else:
                cwnd += 1  # Crescimento linear em Congestion Avoidance

        idx += acks_received  # Move o índice pelo número de pacotes confirmados

if __name__ == '__main__':
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)

    print(f"[SYNC] Envio Cliente")
    send(client, SYNC, -1, False, False)
    id_cliente = receive(client, -1)
    identifier = id_cliente * 100

    try:
        while True:
            messages = []
            while True:
                message = input("Digite sua mensagem aqui (Digite PARE para encerrar o envio em batch): ")
                if message == "PARE":
                    break
                messages.append(message)

            send_window_tahoe(client, messages, identifier)
            identifier += len(messages)

    except KeyboardInterrupt:
        pass
