# VC Outlet · Gerador de etiquetas

Gerador de etiquetas de preço da **VC Outlet**. Cada etiqueta tem **4 × 3 cm**, e a folha de **10 × 15 cm** leva **12 etiquetas**.

Você digita ou escaneia o código, coloca o nome, o preço e o tamanho, vê a folha na hora e imprime. O gerador funciona sem internet, num único arquivo.

> Feito pela [KeyCodes](https://keycodes.com.br).

---

## Como usar (na loja)

1. Baixe o `index.html` e abra no **Chrome**. Não precisa instalar nada nem estar conectado.
2. Clique no campo **Código de barras** e passe o leitor, ou digite o código.
   - O Enter do leitor pula pro campo **Nome**, e outro Enter pula pro **Preço**.
   - Se esse código já foi impresso antes, o nome, o preço e o tamanho aparecem sozinhos.
3. Escolha o **tamanho** e a **quantidade**.
4. Pra trocar só algumas etiquetas, **toque nelas na prévia da folha** e escolha uma opção:
   - **Produto novo:** cria um produto só pra essas etiquetas.
   - **Um produto da lista:** coloca um produto que já está na folha.
   - **Deixar vazia:** a posição não é impressa.
5. Clique em **Imprimir** e, na janela de impressão, escolha:
   - papel **10 × 15 cm** (às vezes aparece como 4 × 6 pol.)
   - margens **Nenhuma**
   - escala **100%**
   - impressão **sem margem**, se a impressora tiver

   Pra mandar o arquivo pra uma gráfica, use **Baixar PDF**.
6. Corte **no meio da linha cinza**. A sobra de 2 × 3 cm vai fora.

### Recentes

Toda folha que você imprime ou baixa fica salva em **Recentes**:

- **Repetir a última folha:** refaz a folha igual, posição por posição. As últimas 10 folhas ficam guardadas.
- **Produtos recentes:** a lista tem busca por nome ou código, e a busca funciona sem acento. Ela guarda até 300 produtos.

O histórico fica salvo **no navegador daquele computador** (`localStorage`). Por isso, abra sempre o mesmo arquivo, no mesmo navegador. Se os dados do navegador forem limpos, o histórico se perde.

### Como o código de barras é criado

| O que você digita | O que o gerador faz |
|---|---|
| 13 números | Confere o último dígito (verificador). Se estiver errado, mostra o certo e bloqueia a impressão até corrigir. |
| 12 números | Se for um código **UPC** (produto importado dos EUA), aceita como está. Se não for, calcula o 13º dígito. |
| 1 a 11 números (ex.: `1402`) | Cria um **código interno da loja**: `2` + a referência completada com zeros + o verificador. A mesma referência gera sempre o mesmo código. |
| Nada | O botão **Gerar novo** cria um código interno que não se repete. |

Os códigos que começam com **2** são a faixa reservada pela GS1 pra uso interno da loja. Eles nunca coincidem com o código de fábrica de outro produto. Pro caixa reconhecer, o código precisa estar cadastrado no produto no sistema da loja.

---

## Estrutura

```
index.html                  gerador pronto (montado pelo build); é o arquivo que vai pra loja
gerador/
  gerador.src.html          código-fonte da página (HTML + CSS + JS)
  build.py                  junta o código-fonte com o logo e as fontes e gera o index.html
  testes/                   testes no Chromium (Playwright) e conferência dos PDFs
etiqueta/                   ferramentas em Python (logo, fontes e PDF de referência)
  logo_trace.py             transforma o logo (JPG) em contornos vetoriais → logo_vc.json
  export_assets.py          extrai os contornos das letras usadas → assets.json
  label.py · sheet.py       desenho de referência da etiqueta e da folha (reportlab)
  ean13.py · vtext.py       código de barras EAN-13 e texto convertido em curva
  verify.py                 decodifica os códigos de barras de um PDF (OpenCV)
  guide.py · preview.py     guia de corte e prancha de aprovação
  src/logo-vc.jpg           logo original
```

### Organização do `gerador.src.html`

| Seção | O que faz |
|---|---|
| 1. Assets | Logo e letras já em contorno, injetados pelo build. A página não carrega nenhuma fonte de fora. |
| 2. Geometria | Medidas da etiqueta em mm, as 12 posições da folha e as linhas de corte. |
| 3. EAN-13 | Codificação, dígito verificador, UPC e interpretação do que foi digitado. |
| 4. Preço | Lê o preço no formato brasileiro (`119,99`, `1.049,90`) e formata. |
| 5. Desenho | Transforma a etiqueta numa lista de formas em mm (caminhos, degradê e traços). |
| 6. Motor SVG | Desenha essa lista na prévia da tela. |
| 7. Motor PDF | Escreve um PDF vetorial direto, sem biblioteca, com o degradê do logo e compressão. |
| 8. Estado | Produtos, o produto de cada posição da folha (`slots`) e o rascunho salvo. |
| 9. Interface | Cartões de produto, seleção de posições na folha e avisos. |
| 9b. Recentes | Histórico, preenchimento pelo código, repetir folha e começar folha nova. |
| 10. Download | Gera o PDF e entrega o arquivo. |
| 10b. Impressão | Monta as páginas com tamanho 100 × 150 mm (`@page`) e chama `window.print()`. |

---

## Decisões técnicas

- **A mesma descrição de desenho alimenta a tela e o PDF.** A etiqueta é descrita uma vez como uma lista de formas, e a prévia na tela e o PDF são feitos a partir dela. Por isso, o que aparece na tela é o que sai impresso.
- **PDF escrito na mão, sem biblioteca.** Funciona sem internet, o arquivo é pequeno (cerca de 50 KB por folha) e a medida da página sai exatamente 100 × 150 mm.
- **Letras em contorno.** O texto entra no arquivo já desenhado, como formas. Por isso a página não depende de fonte instalada nem de baixar fonte. A desvantagem: trocar a fonte exige rodar o `export_assets.py` de novo.
- **Barras 0,02 mm mais finas.** A largura base de cada barra é 0,25 mm, que corresponde a 2 pontos numa impressora de 203 dpi. Deixar cada barra 0,02 mm mais fina compensa a tinta que espalha no papel e afasta as bordas da divisa entre pontos. Sem isso, a impressora de 203 dpi engrossava cada barra em 1 ponto.
- **12 por folha é o máximo possível.** Cabe uma coluna de etiquetas deitadas (4 cm de largura) e duas colunas em pé (3 cm cada), somando 10 cm. Sobram só 2 × 3 cm, e todos os cortes vão de ponta a ponta da folha.
- **Imprimir só no arquivo.** Dentro do claude.ai a página roda num quadro que bloqueia a janela de impressão, então lá só aparece o botão Baixar PDF.

---

## Desenvolvimento

```bash
pip install -r requirements.txt     # ferramentas Python (só pra mexer no logo/fontes e nos testes)
npm install                         # Playwright, pros testes
npm run build                       # gera index.html
npm test                            # build + testes no navegador + conferência dos PDFs
```

**Pra mudar o logo:**

```bash
cd etiqueta
python3 logo_trace.py src/logo-vc.jpg logo_vc.json
python3 export_assets.py assets.json
```

Depois disso, rode `npm run build`.

**Fontes:**
- Preço: TeX Gyre Heros Condensed Bold.
- OUTLET: TeX Gyre Adventor Bold.
- Textos e dígitos: Inter.

São todas de licença aberta (GUST Font License e SIL OFL). Os caminhos ficam em `etiqueta/vtext.py`. Pra usar a fonte definitiva da marca, troque o caminho ali e rode o `export_assets.py`.

### O que os testes conferem

- Trocar 3 etiquetas, deixar uma posição vazia, aumentar a quantidade, abrir uma segunda folha, desfazer e recarregar a página.
- O nome do produto e a sequência código → Enter → nome → Enter → preço.
- Recentes: gravar ao imprimir, preencher pelo código, repetir folha e buscar sem acento.
- Imprimir: uma página por folha.
- PDFs:
  - cada página com exatamente 100 × 150 mm
  - todos os códigos de barras lidos em 300 dpi e em 203 dpi
  - posição vazia sem código

---

## Pendências

- [ ] Confirmar o nome da marca embaixo do logo: OUTLET ou IMPORTADOS.
- [ ] Trocar as fontes provisórias pela fonte definitiva da marca.
- [ ] Imprimir de verdade na impressora da loja e testar com o leitor do caixa.
- [ ] Backup do histórico (exportar e importar um arquivo).
