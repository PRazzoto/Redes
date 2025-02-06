def criar_arquivo_texto_9MB(nome_arquivo="largeFile.txt"):
    tamanho_desejado = 11 * 1024 * 1024  # 9MB em bytes
    # Texto base a ser repetido. Você pode modificar esse conteúdo conforme desejar.
    texto_base = "Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n"

    with open(nome_arquivo, "w", encoding="utf-8") as arquivo:
        # Escreve o texto repetidamente até atingir (ou ultrapassar) o tamanho desejado.
        while arquivo.tell() < tamanho_desejado:
            arquivo.write(texto_base)

    print(f"Arquivo de texto '{nome_arquivo}' criado com aproximadamente 11MB.")


# Exemplo de uso:
if __name__ == "__main__":
    criar_arquivo_texto_9MB()
