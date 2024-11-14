import socket
import hashlib
import time
import random

# Configuração do Cliente
SERVER_IP = "127.0.0.1"  # Endereço IP do servidor
SERVER_PORT = 12345
CHUNK_SIZE = 1024  # Deve corresponder ao CHUNK_SIZE do servidor
BUFFER_SIZE = 2048  # Deve ser >= CHUNK_SIZE + tamanho do cabeçalho
PACKET_LOSS_PROBABILITY = 0.1  # Probabilidade de descartar um chunk (10%)
MAX_RESEND_REQUEST_SIZE = (
    512  # Tamanho máximo da mensagem de solicitação de retransmissão (em bytes)
)


def create_checksum(data):
    return hashlib.md5(data).hexdigest()


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(15)  # Define o timeout para receber dados

    print("Cliente iniciado. Digite 'sair' para encerrar.")

    while True:
        # Entrada do usuário para o nome do arquivo
        filename = input("Digite o nome do arquivo a ser requisitado: ")
        if filename.lower() == "sair":
            print("Encerrando o cliente.")
            break

        request = f"GET {filename}"
        client_socket.sendto(request.encode(), (SERVER_IP, SERVER_PORT))
        print(f"Solicitado arquivo '{filename}' ao servidor.")

        # Variáveis para controle
        received_chunks = {}
        total_chunks = None
        retries = 0
        max_retries = 5

        # Recepção da confirmação e total de chunks
        while True:
            try:
                response, _ = client_socket.recvfrom(BUFFER_SIZE)
                if response == b"OK":
                    total_chunks_data, _ = client_socket.recvfrom(BUFFER_SIZE)
                    total_chunks = int(total_chunks_data.decode())
                    print(f"Total de chunks a receber: {total_chunks}")
                    break
                elif response.startswith(b"ERROR"):
                    print(response.decode())
                    break
                else:
                    print("Resposta inesperada do servidor.")
                    break
            except socket.timeout:
                retries += 1
                if retries > max_retries:
                    print("Servidor não respondeu. Tentativas excedidas.")
                    break
                print("Timeout ao esperar resposta do servidor. Tentando novamente...")
                client_socket.sendto(request.encode(), (SERVER_IP, SERVER_PORT))

        if total_chunks is None:
            continue  # Pular para a próxima iteração se não recebeu o total de chunks

        # Recepção dos chunks
        retry_count = 0
        while len(received_chunks) < total_chunks and retry_count < max_retries:
            try:
                packet, _ = client_socket.recvfrom(BUFFER_SIZE)

                if packet == b"EOF":
                    print("Recebido pacote EOF.")
                    break

                # Simulação de perda de pacote (descarte aleatório)
                if random.random() < PACKET_LOSS_PROBABILITY:
                    print(
                        "Chunk descartado aleatoriamente para simular perda de pacote."
                    )
                    continue  # Descartar o chunk e continuar para o próximo

                # Processamento do pacote
                first_pipe = packet.find(b"|")
                second_pipe = packet.find(b"|", first_pipe + 1)
                header_bytes = packet[: second_pipe + 1]
                chunk_data = packet[second_pipe + 1 :]
                header = header_bytes.decode()
                header_parts = header.strip("|").split("|")
                chunk_num = int(header_parts[0])
                checksum = header_parts[1]

                # Verifica se o chunk já foi recebido
                if chunk_num in received_chunks:
                    continue

                # Verifica o checksum
                if create_checksum(chunk_data) == checksum:
                    received_chunks[chunk_num] = chunk_data
                    print(
                        f"Chunk {chunk_num} recebido e verificado ({len(received_chunks)}/{total_chunks})"
                    )
                    retry_count = 0  # Reseta o contador de retries em caso de sucesso
                else:
                    print(f"Checksum incorreto para o chunk {chunk_num}.")
            except socket.timeout:
                retry_count += 1
                print(
                    f"Timeout ao receber dados. Tentativa {retry_count}/{max_retries}"
                )
                if retry_count >= max_retries:
                    print("Tentativas excedidas. Encerrando recebimento.")
                    break
                continue
            except Exception as e:
                print(f"Ocorreu um erro: {e}")
                break

        # Verificação de chunks faltantes
        missing_chunks = set(range(total_chunks)) - set(received_chunks.keys())
        if missing_chunks:
            print(f"Chunks faltantes: {missing_chunks}")
            # Dividir a lista de chunks faltantes em blocos menores
            missing_chunks_list = sorted(list(missing_chunks))
            chunks_per_request = 50  # Ajuste este valor conforme necessário
            for i in range(0, len(missing_chunks_list), chunks_per_request):
                chunk_block = missing_chunks_list[i : i + chunks_per_request]
                resend_request = f"RESEND {' '.join(map(str, chunk_block))}"
                # Verificar se a mensagem não excede o tamanho máximo permitido
                while len(resend_request.encode()) > MAX_RESEND_REQUEST_SIZE:
                    # Reduzir o número de chunks no bloco
                    chunks_per_request -= 5
                    chunk_block = missing_chunks_list[i : i + chunks_per_request]
                    resend_request = f"RESEND {' '.join(map(str, chunk_block))}"
                    if chunks_per_request <= 0:
                        print(
                            "Erro: Não foi possível criar uma solicitação de retransmissão dentro do limite de tamanho."
                        )
                        return

                client_socket.sendto(resend_request.encode(), (SERVER_IP, SERVER_PORT))
                print(f"Solicitada retransmissão dos chunks: {chunk_block}")

                # Recebe os chunks retransmitidos
                retry_count = 0
                while chunk_block and retry_count < max_retries:
                    try:
                        packet, _ = client_socket.recvfrom(BUFFER_SIZE)

                        if packet == b"EOF":
                            print("Recebido pacote EOF após retransmissão.")
                            break

                        # Simulação de perda de pacote na retransmissão
                        if random.random() < PACKET_LOSS_PROBABILITY:
                            print("Chunk retransmitido descartado aleatoriamente.")
                            continue  # Descartar o chunk e continuar para o próximo

                        # Processamento do pacote
                        first_pipe = packet.find(b"|")
                        second_pipe = packet.find(b"|", first_pipe + 1)
                        header_bytes = packet[: second_pipe + 1]
                        chunk_data = packet[second_pipe + 1 :]
                        header = header_bytes.decode()
                        header_parts = header.strip("|").split("|")
                        chunk_num = int(header_parts[0])
                        checksum = header_parts[1]

                        if chunk_num in chunk_block:
                            if create_checksum(chunk_data) == checksum:
                                received_chunks[chunk_num] = chunk_data
                                chunk_block.remove(chunk_num)
                                print(
                                    f"Chunk faltante {chunk_num} recebido ({len(received_chunks)}/{total_chunks})"
                                )
                                retry_count = (
                                    0  # Reseta o contador de retries em caso de sucesso
                                )
                            else:
                                print(
                                    f"Checksum incorreto para o chunk retransmitido {chunk_num}"
                                )
                    except socket.timeout:
                        retry_count += 1
                        print(
                            f"Timeout ao receber dados retransmitidos. Tentativa {retry_count}/{max_retries}"
                        )
                        if retry_count >= max_retries:
                            print("Tentativas excedidas ao receber chunks faltantes.")
                            break
                        continue
                    except Exception as e:
                        print(f"Ocorreu um erro: {e}")
                        break
        else:
            print("Todos os chunks foram recebidos com sucesso.")

        # Montagem do arquivo recebido
        if len(received_chunks) == total_chunks:
            with open(f"received_{filename}", "wb") as f:
                for chunk_num in sorted(received_chunks.keys()):
                    f.write(received_chunks[chunk_num])
            print(f"Arquivo '{filename}' recebido com sucesso.")
        else:
            print("Não foi possível receber todos os chunks.")

    # Fechamento do socket após sair do loop
    client_socket.close()
    print("Conexão encerrada.")


if __name__ == "__main__":
    main()
