import socket
import os
import hashlib

# Configuração do Servidor
SERVER_IP = "0.0.0.0"  # Escuta em todas as interfaces de rede
SERVER_PORT = 12345
CHUNK_SIZE = 1024  # Tamanho de cada chunk (1 KB)
BUFFER_SIZE = 2048  # Deve ser >= CHUNK_SIZE + tamanho do cabeçalho


def create_checksum(data):
    return hashlib.md5(data).hexdigest()


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((SERVER_IP, SERVER_PORT))
    print(f"Servidor ouvindo na porta {SERVER_PORT}")

    client_files = {}  # Dicionário para mapear cliente ao arquivo

    while True:
        server_socket.settimeout(None)
        print("\nAguardando nova requisição de cliente...")
        message, client_address = server_socket.recvfrom(BUFFER_SIZE)
        request = message.decode()

        if request.startswith("GET"):
            _, filename = request.split()
            if os.path.isfile(filename):
                # Enviar confirmação e número total de chunks
                server_socket.sendto(b"OK", client_address)
                file_size = os.path.getsize(filename)
                total_chunks = file_size // CHUNK_SIZE + (file_size % CHUNK_SIZE > 0)
                server_socket.sendto(str(total_chunks).encode(), client_address)
                print(
                    f"Cliente {client_address} requisitou o arquivo '{filename}'. Total de chunks a enviar: {total_chunks}"
                )

                # Armazenar o nome do arquivo associado ao cliente
                client_files[client_address] = filename

                # Envio dos chunks do arquivo
                with open(filename, "rb") as f:
                    chunk_num = 0
                    while True:
                        chunk_data = f.read(CHUNK_SIZE)
                        if not chunk_data:
                            break
                        checksum = create_checksum(chunk_data)
                        header = f"{chunk_num}|{checksum}|".encode()
                        packet = header + chunk_data

                        # Envia o pacote
                        server_socket.sendto(packet, client_address)
                        print(f"Enviado chunk {chunk_num}/{total_chunks - 1}")
                        chunk_num += 1

                # Envia o pacote EOF
                eof_packet = b"EOF"
                server_socket.sendto(eof_packet, client_address)
                print("Pacote EOF enviado.")
            else:
                # Arquivo não encontrado
                error_msg = "ERROR: File not found"
                server_socket.sendto(error_msg.encode(), client_address)
                print(
                    f"Arquivo '{filename}' não encontrado. Mensagem de erro enviada ao cliente."
                )
        elif request.startswith("RESEND"):
            # Extrai os números dos chunks faltantes
            parts = request.split()
            if len(parts) > 1:
                missing_chunks = parts[1:]
                print(
                    f"Cliente {client_address} solicitou retransmissão dos chunks: {missing_chunks}"
                )

                # Recupera o nome do arquivo associado ao cliente
                filename = client_files.get(client_address, None)
                if filename and os.path.isfile(filename):
                    with open(filename, "rb") as f:
                        for chunk_num_str in missing_chunks:
                            chunk_num = int(chunk_num_str)
                            f.seek(chunk_num * CHUNK_SIZE)
                            chunk_data = f.read(CHUNK_SIZE)
                            checksum = create_checksum(chunk_data)
                            header = f"{chunk_num}|{checksum}|".encode()
                            packet = header + chunk_data
                            server_socket.sendto(packet, client_address)
                            print(f"Reenviado chunk {chunk_num}")
                    # Envia o pacote EOF após a retransmissão
                    server_socket.sendto(b"EOF", client_address)
                    print("Pacote EOF enviado após retransmissão.")
                else:
                    error_msg = "ERROR: File not found"
                    server_socket.sendto(error_msg.encode(), client_address)
                    print(f"Arquivo '{filename}' não encontrado durante retransmissão.")
            else:
                print(f"Requisição de retransmissão inválida de {client_address}.")
        else:
            # Requisição inválida
            error_msg = "ERROR: Invalid request"
            server_socket.sendto(error_msg.encode(), client_address)
            print(
                f"Recebida requisição inválida de {client_address}. Mensagem de erro enviada."
            )


if __name__ == "__main__":
    main()
