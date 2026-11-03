# Fontes & Referências do Poster

Página estática criada para documentar e apresentar de forma visual, interativa e rigorosa as fontes bibliográficas e normas do poster técnico.

## Tópicos e Normas Incluídas

1. **NFC (Near Field Communication)**
   - ISO/IEC 18092 (NFCIP-1)
   - ISO/IEC 14443 (Partes 1 a 4) Tipos A e B
   - JIS X 6319-4 (Sony FeliCa)

2. **OSPF (Open Shortest Path First)**
   - **1989** | OSPFv1 na RFC 1131 — Base experimental
   - **1991** | OSPFv2 na RFC 1247 (John Moy) — Versão robusta para IPv4
   - **1998** | OSPFv2 consolidado na RFC 2328 — Versão atual para IPv4 (Internet Standard STD 54)
   - **1999** | OSPFv3 (RFC 2740 / RFC 5340) — Suporte a IPv6

3. **SCTP (Stream Control Transmission Protocol)**
   - RFC 9260 (2022) — Especificação atual e padrão consolidado IETF
   - RFC 4960 (2007) — Norma anterior de referência
   - RFC 2960 (2000) — Especificação original
   - RFC 3286 (2002) — Introdução arquitetural ao SCTP

4. **MCP (Model Context Protocol)**
   - Especificação Oficial do Model Context Protocol (Anthropic & LF Projects)
   - Hou, X., et al. (2026). *Model Context Protocol (MCP): Landscape, Security Threats, and Future Research Directions*. ACM TOSEM.
   - Hasan, M. M., et al. (2026). *Model Context Protocol (MCP) at First Glance: Studying Security and Maintainability*. ACM TOSEM.
   - Li, Z., et al. (2025). *We Urgently Need Privilege Management in MCP*. IEEE MASS.

## Funcionalidades da Página

- **Tema Claro / Escuro (Dark & Light Mode)** com persistência em cache local (`localStorage`).
- **Pesquisa em tempo real** por termo, autor, norma ou código RFC.
- **Filtros por categoria** (NFC, OSPF, SCTP, MCP).
- **Linha temporal visual e interativa** para a evolução histórica do OSPF.
- **Botões "Copiar Citação"** em cada entrada para transferência rápida formatada.
- **Links diretos** para a ISO, IETF Datatracker, Sony FeliCa, Anthropic e bases ACM / IEEE.
- **Suporte a Impressão / PDF** (`window.print` e `@media print`) otimizado em escala de cinza/preto e branco para gerar folhetos de referências.

## Como Visualizar

Basta abrir o ficheiro `index.html` em qualquer navegador web (Chrome, Firefox, Edge, Safari):

```bash
# Exemplo no Linux:
xdg-open index.html
```
