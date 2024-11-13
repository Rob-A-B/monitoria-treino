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
            print(f"RECEIVED RESPONSE FROM SERVER {msg}")
            return msg_id  # Retorna o ID da mensagem para ACKs normais

    except RecvTimeout:
        print("[ERROR] Timeout while waiting for response")
        return None
    except ValueError as e:
        print(f"[ERROR] Value error: {e}")
        return None

def send(client, msg, identifier, insert_error=False, insert_error_hash=False, simulate_timeout=False, retransmit_attempts=3):
    try:
        content = str(msg).encode(FORMAT)

        if insert_error_hash:
            content += b'0000'  # Adiciona um erro intencional no hash
        else:
            content = add_hash(content)

        # Simula erro de checksum, se necessário
        checksum = (len(content) + identifier) * (1 if not insert_error else -1)
        header = '\n'.join([str(len(content)), str(identifier), str(checksum)]).encode(FORMAT)
        header += b' ' * (HEADER - len(header))
        message = (header + content)

        if simulate_timeout:
            print(f"[SIMULATION] Timeout simulated for sequence {identifier}")
            return  # Simula um timeout ao não enviar a mensagem

        client.send(message)
    except BrokenPipeError:
        print("[ERROR] Conexão quebrada")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        if retransmit_attempts > 0:
            return send(client, msg, identifier, insert_error, insert_error_hash, simulate_timeout, retransmit_attempts=retransmit_attempts-1)

def send_window_tahoe(client, messages, start_sequence):
    global cwnd, ssthresh
    idx = 0  # Índice do início da janela

    while idx < len(messages):
        # Limita o tamanho da janela de envio com base em cwnd
        end_idx = idx + int(cwnd)
        window = messages[idx:end_idx]

        print(f"Enviando janela: {window}")  # Imprime a janela atual
        for i, message in enumerate(window):
            error_type = input(f"Especifique o tipo de erro para a mensagem '{message}' (echeck/ehash/etimeout/none): ").strip().lower()

            insert_error = (error_type == 'echeck')
            insert_error_hash = (error_type == 'ehash')
            simulate_timeout = (error_type == 'etimeout')

            send(client, message, start_sequence + i, insert_error, insert_error_hash, simulate_timeout)

        # Aguarda ACKs e ajusta cwnd de acordo
        acks_received = 0
        for i in range(len(window)):
            if simulate_timeout:
                print("[INFO] Timeout foi simulado, não aguardando ACK")
                break

            try:
                ack_id = receive(client, start_sequence + i)
                print(f"ACK received for sequence {ack_id}")
                acks_received += 1
            except RecvTimeout:
                print("Timeout detected, entrando em Slow Start")
                ssthresh = max(cwnd // 2, 1)
                cwnd = 1  # Reinicia a janela de congestionamento
                start_sequence -= (len(window) - acks_received)  # Reajusta a sequência
                idx -= (len(window) - acks_received)  # Reajusta o índice para retransmissão
                break

        # Ajusta cwnd após receber ACKs
        if acks_received == len(window):
            if cwnd < ssthresh:
                cwnd *= 2  # Crescimento exponencial em Slow Start
            else:
                cwnd += 1  # Crescimento linear em Congestion Avoidance

        # Move o índice pelo número de pacotes confirmados
        idx += acks_received
        start_sequence += acks_received  # Atualiza a sequência de início

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
