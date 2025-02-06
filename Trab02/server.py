#!/usr/bin/env python3
import socket
import threading
import os
import hashlib

# Lista global de clientes e lock para acesso seguro
clients = []
clients_lock = threading.Lock()


def broadcast_message(message, exclude_conn=None):
    """
    Envia uma mensagem para todos os clientes conectados, exceto o que estiver em exclude_conn.
    """
    with clients_lock:
        for client in clients:
            conn, addr = client
            if conn != exclude_conn:
                try:
                    conn.sendall(message.encode())
                except Exception as e:
                    print(f"Erro ao enviar para {addr}: {e}")


def handle_client(conn, addr):
    """Trata a conexão de cada cliente em uma thread separada."""
    print(f"Cliente conectado: {addr}")
    while True:
        try:
            data = conn.recv(4096)
            if not data:
                print(f"Conexão encerrada pelo cliente {addr}")
                break

            command = data.decode().strip()

            if command == "Sair":
                print(f"Cliente {addr} pediu para sair.")
                break

            elif command.startswith("Arquivo"):
                parts = command.split(maxsplit=1)
                if len(parts) != 2:
                    conn.sendall(
                        "Formato de comando incorreto. Use: Arquivo <nome>\n".encode()
                    )
                    continue

                filename = parts[1]
                print(f"Requisição recebida de {addr} para o arquivo '{filename}'.")

                if not os.path.exists(filename):
                    header = (
                        f"NOME:{filename}\n"
                        f"TAMANHO:0\n"
                        f"HASH:\n"
                        f"STATUS:NOK\n"
                        f"HEADER_END\n"
                    )
                    conn.sendall(header.encode())
                    print(
                        f"Arquivo '{filename}' não encontrado. Notificando o cliente {addr}."
                    )
                    continue

                filesize = os.path.getsize(filename)
                # Calcula o hash do arquivo (SHA-256)
                sha256_hash = hashlib.sha256()
                with open(filename, "rb") as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        sha256_hash.update(chunk)
                file_hash = sha256_hash.hexdigest()

                header = (
                    f"NOME:{filename}\n"
                    f"TAMANHO:{filesize}\n"
                    f"HASH:{file_hash}\n"
                    f"STATUS:OK\n"
                    f"HEADER_END\n"
                )
                conn.sendall(header.encode())
                print(
                    f"Iniciando envio do arquivo '{filename}' para {addr}. Tamanho: {filesize} bytes."
                )

                # Envia os dados do arquivo em blocos
                total_sent = 0
                with open(filename, "rb") as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        conn.sendall(chunk)
                        total_sent += len(chunk)
                        print(
                            f"Enviando arquivo '{filename}' para {addr}: {total_sent}/{filesize} bytes enviados."
                        )
                print(f"Envio do arquivo '{filename}' para {addr} concluído.")

            else:
                # Qualquer outra mensagem é tratada como chat (não há opção explícita de chat)
                print(f"[Chat de {addr}]: {command}")
                broadcast_message(f"[{addr}] {command}\n", exclude_conn=conn)

        except Exception as e:
            print(f"Erro com o cliente {addr}: {e}")
            break

    # Remove o cliente da lista e fecha a conexão
    with clients_lock:
        for client in clients:
            if client[0] == conn:
                clients.remove(client)
                break
    conn.close()
    print(f"Conexão com {addr} encerrada.")


def server_console_input():
    """
    Lê o que o operador digita no console do servidor e envia a todos os clientes.
    Se o operador digitar "sair", o servidor encerra.
    """
    while True:
        try:
            message = input()  # Aguarda a entrada do operador
            if message.strip().lower() == "sair":
                print("Encerrando servidor por comando do operador.")
                os._exit(0)
            broadcast_message(f"\n[Server] {message}\n")
        except Exception as e:
            print(f"Erro na entrada do servidor: {e}")


def main():
    host = "0.0.0.0"
    port = 12345  # Porta escolhida (maior que 1024)
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((host, port))
    server_sock.listen(5)
    print(f"Servidor iniciado em {host}:{port}")

    # Inicia a thread para ler entradas do operador do servidor
    threading.Thread(target=server_console_input, daemon=True).start()

    while True:
        try:
            conn, addr = server_sock.accept()
            with clients_lock:
                clients.append((conn, addr))
            threading.Thread(target=handle_client, args=(conn, addr)).start()
        except Exception as e:
            print(f"Erro ao aceitar conexão: {e}")
            break


if __name__ == "__main__":
    main()
