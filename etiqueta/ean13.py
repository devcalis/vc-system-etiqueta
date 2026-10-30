"""
ean13.py — Codificador EAN-13 sem dependências.

- check_digit(): dígito verificador GS1 (pesos 1/3 alternados).
- encode(): devolve a sequência de 95 módulos ('1' = barra, '0' = espaço).
- random_store_code(): código de USO INTERNO da loja. Prefixo GS1 "2"
  (faixa 200–299, circulação restrita) — é o que se usa pra etiqueta própria,
  porque não colide com nenhum GTIN real de fábrica.
"""
import random

# Tabelas de codificação (L = ímpar, G = par, R = lado direito)
L = ["0001101", "0011001", "0010011", "0111101", "0100011",
     "0110001", "0101111", "0111011", "0110111", "0001011"]
G = ["0100111", "0110011", "0011011", "0100001", "0011101",
     "0111001", "0000101", "0010001", "0001001", "0010111"]
R = ["1110010", "1100110", "1101100", "1000010", "1011100",
     "1001110", "1010000", "1000100", "1001000", "1110100"]
# Paridade do lado esquerdo definida pelo 1º dígito
PARITY = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
          "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"]

START = END = "101"
CENTER = "01010"


def check_digit(first12: str) -> int:
    if len(first12) != 12 or not first12.isdigit():
        raise ValueError("EAN-13 precisa de 12 dígitos antes do verificador")
    s = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(first12))
    return (10 - s % 10) % 10


def full_code(first12: str) -> str:
    return first12 + str(check_digit(first12))


def encode(code13: str) -> str:
    if len(code13) != 13 or not code13.isdigit():
        raise ValueError("EAN-13 precisa de 13 dígitos")
    if check_digit(code13[:12]) != int(code13[12]):
        raise ValueError(f"Dígito verificador inválido em {code13}")
    parity = PARITY[int(code13[0])]
    left = "".join((L if p == "L" else G)[int(d)] for p, d in zip(parity, code13[1:7]))
    right = "".join(R[int(d)] for d in code13[7:13])
    bits = START + left + CENTER + right + END
    assert len(bits) == 95
    return bits


def guard_mask() -> list:
    """True nos módulos das barras-guia (que descem mais que as outras)."""
    m = [False] * 95
    for i in list(range(0, 3)) + list(range(45, 50)) + list(range(92, 95)):
        m[i] = True
    return m


def random_store_code(rng: random.Random) -> str:
    body = "2" + "".join(str(rng.randint(0, 9)) for _ in range(11))
    return full_code(body)


if __name__ == "__main__":
    # sanidade com o código de exemplo enviado (3 229980 001402)
    assert check_digit("322998000140") == 2, "verificador do exemplo não bate"
    print(encode("3229980001402"))
    print("ok")
