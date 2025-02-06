#!/usr/bin/env python3
import socket
import threading
import os
import hashlib
from urllib.parse import urlparse, parse_qs
import mimetypes


def serve_file(conn, addr, filename):
    """
    Verifica se o arquivo existe e, se existir, envia-o com os cabeçalhos HTTP adequados.
    Se o arquivo não existir, envia uma resposta 404.
    """
    if not os.path.exists(filename):
        response_body = f"Arquivo '{filename}' nao encontrado."
        response = (
            "HTTP/1.1 404 Not Found\r\n"
            f"Content-Length: {len(response_body)}\r\n"
            "Content-Type: text/plain\r\n\r\n" + response_body
        )
        conn.sendall(response.encode())
        print(f"[{addr}] Arquivo '{filename}' nao encontrado.")
        return

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

    # Determina o Content-Type com base na extensão do arquivo
    content_type, _ = mimetypes.guess_type(filename)
    if content_type is None:
        content_type = "text/plain"

    headers = [
        "HTTP/1.1 200 OK",
        f"Content-Length: {filesize}",
        f"X-NOME: {filename}",
        f"X-TAMANHO: {filesize}",
        f"X-HASH: {file_hash}",
        "X-STATUS: OK",
        f"Content-Type: {content_type}",
        "",  # Linha em branco que separa cabeçalhos do corpo
        "",
    ]
    header_str = "\r\n".join(headers)
    conn.sendall(header_str.encode())
    print(
        f"[{addr}] Iniciando envio do arquivo '{filename}' ({filesize} bytes, Content-Type: {content_type})."
    )
    total_sent = 0
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            conn.sendall(chunk)
            total_sent += len(chunk)
            print(f"[{addr}] {total_sent}/{filesize} bytes enviados.")
    print(f"[{addr}] Envio do arquivo '{filename}' concluido.")


def handle_client(conn, addr):
    print(f"Conexao estabelecida com {addr}")
    try:
        # Lê a requisição HTTP (limitando a 8KB para este exemplo)
        request = conn.recv(8192).decode()
        if not request:
            conn.close()
            return

        # Exibe a primeira linha da requisição (por exemplo: GET /Arquivo?nome=exemplo.html HTTP/1.1)
        request_line = request.splitlines()[0]
        print(f"[{addr}] Requisição: {request_line}")

        parts = request_line.split()
        if len(parts) < 2:
            conn.close()
            return

        method, path = parts[0], parts[1]
        parsed_url = urlparse(path)

        # Se a URL for /Arquivo, usamos o parâmetro de query string para obter o nome do arquivo
        if parsed_url.path.lower() == "/arquivo":
            qs = parse_qs(parsed_url.query)
            filename_list = qs.get("nome")
            if not filename_list:
                response_body = "Parametro 'nome' ausente."
                response = (
                    "HTTP/1.1 400 Bad Request\r\n"
                    f"Content-Length: {len(response_body)}\r\n"
                    "Content-Type: text/plain\r\n\r\n" + response_body
                )
                conn.sendall(response.encode())
            else:
                filename = filename_list[0]
                serve_file(conn, addr, filename)

        # Se a URL for a raiz, envia uma página HTML com instruções
        elif parsed_url.path == "/":
            response_body = (
                "<html>\n"
                "<head><title>Pagina Inicial</title></head>\n"
                "<body>\n"
                "Bem-vindo ao servidor TCP com sockets!<br>\n"
                "Para solicitar um arquivo via query, use a URL:<br>\n"
                "/Arquivo?nome=seuarquivo.ext<br>\n"
                "Ou acesse diretamente um arquivo, por exemplo:<br>\n"
                "http://localhost:8080/exemplo.html<br>\n"
                "Certifique-se de que os arquivos estao na mesma pasta do servidor.\n"
                "</body>\n"
                "</html>"
            )
            response = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Length: {len(response_body)}\r\n"
                "Content-Type: text/html\r\n\r\n" + response_body
            )
            conn.sendall(response.encode())

        # Para qualquer outro caminho, trata-o como uma requisição direta de arquivo
        else:
            # Remove a barra inicial para obter o nome do arquivo
            filename = parsed_url.path.lstrip("/")
            serve_file(conn, addr, filename)

    except Exception as e:
        print(f"Erro com {addr}: {e}")
    finally:
        conn.close()
        print(f"Conexao com {addr} encerrada.")


def main():
    host = "0.0.0.0"
    port = 8080  # Porta escolhida (maior que 1024)
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((host, port))
    server_sock.listen(5)
    print(f"Servidor iniciado em {host}:{port}")

    while True:
        try:
            conn, addr = server_sock.accept()
            # Cria uma thread para tratar cada conexão
            threading.Thread(target=handle_client, args=(conn, addr)).start()
        except Exception as e:
            print("Erro ao aceitar conexao:", e)
            break


if __name__ == "__main__":
    main()
