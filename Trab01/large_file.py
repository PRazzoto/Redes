# create_large_file.py
def main():
    filename = "large_test_file.txt"
    line = "Olá, esse é o meu arquivo gigante para o trabalho 1 de redes de computadores.\n"
    target_size_mb = 15  # Tamanho desejado do arquivo em megabytes
    target_size_bytes = target_size_mb * 1024 * 1024
    current_size = 0

    with open(filename, "w", encoding="utf-8") as f:
        while current_size < target_size_bytes:
            f.write(line)
            current_size += len(line.encode("utf-8"))

    print(
        f"Arquivo '{filename}' criado com sucesso. Tamanho: {current_size / (1024 * 1024):.2f} MB"
    )


if __name__ == "__main__":
    main()
