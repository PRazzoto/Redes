#!/usr/bin/env python3
import socket
import threading
import hashlib


def receive_messages(sock):
    """
    Thread que recebe mensagens do servidor.
    Se detectar um header de arquivo (iniciando com "NOME:"), trata a transferência do arquivo.
    Durante o recebimento, exibe o progresso da transferência.
    """
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print("Conexão encerrada pelo servidor.")
                break

            text = data.decode(errors="ignore")
            if text.startswith("NOME:"):
                # Lê o header completo até encontrar "HEADER_END"
                header_data = text
                while "HEADER_END" not in header_data:
                    more = sock.recv(4096).decode(errors="ignore")
                    header_data += more

                lines = header_data.splitlines()
                header_fields = {}
                for line in lines:
                    if line == "HEADER_END":
                        break
                    if ":" in line:
                        key, value = line.split(":", 1)
                        header_fields[key] = value

                filename = header_fields.get("NOME", "arquivo_recebido")
                filesize = int(header_fields.get("TAMANHO", "0"))
                file_hash = header_fields.get("HASH", "")
                status = header_fields.get("STATUS", "NOK")

                if status != "OK":
                    print(f"Erro: Arquivo '{filename}' não encontrado no servidor.")
                    continue

                print(
                    f"Iniciando recebimento do arquivo '{filename}' com tamanho {filesize} bytes."
                )
                received_bytes = 0
                file_data = b""
                last_printed = 0

                while received_bytes < filesize:
                    chunk = sock.recv(min(4096, filesize - received_bytes))
                    if not chunk:
                        break
                    file_data += chunk
                    received_bytes += len(chunk)
                    # Imprime a cada 1MB recebido ou quando o arquivo estiver completo
                    if (received_bytes - last_printed >= 1024 * 1024) or (
                        received_bytes == filesize
                    ):
                        print(
                            f"Recebendo arquivo '{filename}': {received_bytes}/{filesize} bytes recebidos."
                        )
                        last_printed = received_bytes

                # Salva o arquivo recebido
                with open("recv_" + filename, "wb") as f:
                    f.write(file_data)

                # Verifica a integridade do arquivo recebido (SHA-256)
                sha256_hash = hashlib.sha256()
                sha256_hash.update(file_data)
                received_hash = sha256_hash.hexdigest()

                if received_hash == file_hash:
                    print(
                        f"Arquivo '{filename}' recebido com sucesso e integridade verificada."
                    )
                else:
                    print(f"Arquivo '{filename}' recebido, mas a integridade falhou.")
            else:
                # Mensagens que não sejam transferência de arquivo (chat ou notificações)
                print(text)

        except Exception as e:
            print(f"Erro ao receber dados: {e}")
            break


def main():
    server_host = input("Digite o endereço do servidor: ")
    server_port = int(input("Digite a porta do servidor: "))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_host, server_port))
    print("Conectado ao servidor.")

    # Inicia a thread para receber mensagens do servidor
    threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()

    # Loop principal para enviar comandos ou mensagens
    while True:
        try:
            command = input(
                "Digite o comando (Arquivo <nome> ou Sair) ou uma mensagem para chat: "
            )
            if command.strip() == "":
                continue

            sock.sendall(command.encode())

            if command.strip() == "Sair":
                print("Encerrando conexão.")
                break
        except Exception as e:
            print(f"Erro ao enviar dados: {e}")
            break

    sock.close()


if __name__ == "__main__":
    main()
