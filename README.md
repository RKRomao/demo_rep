# Fontes & Referências do Poster

Página estática criada para documentar e apresentar de forma visual, interativa e rigorosa as fontes bibliográficas, normas e artigos citados no poster técnico.

Disponível online em: **[https://rkromao.github.io/demo_rep/](https://rkromao.github.io/demo_rep/)**

## Tópicos e Normas Incluídas (31 Fontes)

### 1. NFC (Near Field Communication)
- **ISO/IEC 18092:2023** — Interface and Protocol (NFCIP-1)
- **ISO/IEC 14443 (Partes 1 a 4) Tipos A e B** — Contactless proximity objects
- **JIS X 6319-4** — Sony FeliCa high-speed smartcards
- **ISO/IEC 21481:2021** — NFCIP-2 (Comutação automática entre NFCIP-1, 14443 e 15693)
- **NFC Forum NDEF Technical Specification** — Formato universal de dados em tags
- **EMVCo Contactless Specifications (Book A-D)** — Norma global de cartões e pagamentos móveis
- **Haselsteiner & Breitfuß (2006)** — *Security in Near Field Communication (NFC)* (RFIDSec)

### 2. OSPF (Open Shortest Path First)
- **1989** | RFC 1131 — Base experimental (John Moy)
- **1991** | RFC 1247 — OSPFv2 versão robusta para IPv4
- **1998** | RFC 2328 — OSPFv2 consolidado e *Internet Standard (STD 54)* para IPv4
- **1999** | RFC 2740 — Suporte inicial a IPv6
- **1998** | *OSPF: Anatomy of an Internet Routing Protocol* — Livro canónico de John Moy (Addison-Wesley)
- **2008** | RFC 5340 — OSPF for IPv6 (revisão e consolidação formal)
- **2003 / 2018** | RFC 3630 & RFC 8362 — Traffic Engineering Extensions & OSPFv3 LSA Extensibility
- **2009** | RFC 5709 — OSPFv2 HMAC-SHA Cryptographic Authentication
- **2019** | RFC 8665 — OSPF Extensions for Segment Routing (SR-MPLS / SRv6)

### 3. SCTP (Stream Control Transmission Protocol)
- **RFC 9260 (2022)** — Especificação consolidada atual da IETF (substitui a RFC 4960)
- **RFC 4960 (2007)** — Norma anterior de referência
- **RFC 2960 (2000)** — Especificação original inaugural (SIGTRAN / SS7)
- **RFC 3286 (2002)** — Introdução arquitetural comparativa com TCP/UDP
- **Stewart & Xie (2001)** — *Stream Control Transmission Protocol (SCTP): A Reference Guide* (Addison-Wesley)
- **RFC 3758 (2004)** — PR-SCTP (Partial Reliability Extension para tempo real)
- **RFC 8831 / RFC 8832 (2021)** — WebRTC Data Channels sobre DTLS/SCTP em navegadores
- **3GPP TS 38.413 (5G) & TS 36.413 (4G)** — Protocolo de transporte obrigatório no plano de controlo NGAP e S1AP

### 4. MCP (Model Context Protocol) & Agentes de IA
- **Model Context Protocol Specification** — Anthropic & LF Projects (Padrão aberto)
- **Anthropic Engineering (2024)** — *Introducing the Model Context Protocol*
- **Hou, X., et al. (2026)** — *Model Context Protocol (MCP): Landscape, Security Threats, and Future Research Directions* (ACM TOSEM)
- **Hasan, M. M., et al. (2026)** — *Model Context Protocol (MCP) at First Glance: Studying Security and Maintainability* (ACM TOSEM)
- **Li, Z., et al. (2025)** — *We Urgently Need Privilege Management in MCP* (IEEE MASS)
- **Greshake, K., et al. (2023)** — *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection* (ACM AISEC/WiSec)
- **Schick, T., et al. (2023)** — *Toolformer: Language Models Can Teach Themselves to Use Tools* (NeurIPS 36)

## Funcionalidades da Página

- **Tema Claro / Escuro (Dark & Light Mode)** com persistência em cache local (`localStorage`).
- **Pesquisa em tempo real** instantânea por qualquer termo, autor, norma, ano ou protocolo.
- **Filtros por categoria** com contadores dinâmicos.
- **Linha temporal visual e interativa** da evolução histórica do OSPF.
- **Botões "Copiar Citação"** formatados para utilização direta em trabalhos e relatórios.
- **Links diretos** para repositórios oficiais (IETF Datatracker, ISO, 3GPP, ACM Digital Library, IEEE Xplore, NeurIPS).
- **Suporte a Impressão e PDF** (`@media print`) limpo e profissional.
