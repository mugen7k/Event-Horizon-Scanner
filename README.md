# 🌌 Event Horizon Scanner

Um aplicativo de desktop moderno em Python que transforma sua webcam em um scanner de documentos inteligente. Com uma arquitetura reformulada, ele utiliza Visão Computacional para detecção de bordas em tempo real e a capacidade multimodal do **Google Gemini 2.5 Flash** para extração de alta precisão, correção e tradução de textos.

## ✨ Funcionalidades

* **Detecção Automática (CamScanner Style):** Reconhece as bordas do papel em tempo real e realiza o recorte com correção de perspectiva (*Warp Perspective*) adaptado para um formato vertical mobile (9:16).
* **Visão Multimodal com IA:** O motor visual do Gemini processa a imagem diretamente, eliminando as limitações do OCR tradicional. Ele ignora sombras, ruídos e entende caligrafias com altíssima precisão.
* **Processamento de Texto Avançado:** A IA formata o parágrafo perfeitamente, corrigindo pontuações fantasmas e quebras de linha indesejadas.
* **Tradução Integrada:** Botões seletores dinâmicos (*Segmented Buttons*) para traduzir o texto escaneado automaticamente para Inglês ou Espanhol em uma única requisição.
* **Histórico de Capturas:** Sistema que armazena localmente os textos gerados na sessão, permitindo que o usuário visualize e reabra digitalizações anteriores em um painel com rolagem.
* **Text-to-Speech Neural (TTS):** Geração de áudio narrado (`.mp3`) de forma assíncrona, utilizando vozes neurais e realistas. Conta também com a opção inteligente de "Áudio Resumido".
* **Exportação em PDF:** Salva os resultados automaticamente em um documento PDF limpo e formatado.
* **Interface Gráfica Mobile-First:** UI elegante e responsiva construída com CustomTkinter (Tema Claro/Amarelo), incluindo identidade visual com logotipo, painel dinâmico (*bottom sheet*) e animação de carregamento circular (*spinner*).

## 🛠️ Tecnologias Utilizadas

* **Python 3.x**
* **OpenCV & NumPy** (Processamento Matemático e de Imagem)
* **Google GenAI SDK** (Integração Multimodal com LLM Gemini)
* **CustomTkinter & Tkinter** (Interface Gráfica e Animações em Canvas)
* **Edge TTS & Asyncio** (Geração de Áudio Neural da Microsoft)
* **FPDF & Pillow (PIL)** (Exportação de PDF e Tratamento Dinâmico de Imagens)

## 🚀 Como instalar e rodar

### 1. Pré-requisitos

* Python instalado na sua máquina.
* Uma **API Key** válida do Google Gemini (adicione-a na linha 13 do arquivo principal).

### 2. Instalação

Clone o repositório e instale as bibliotecas necessárias utilizando o gerenciador de pacotes `pip`:

```bash
pip install -r requirements.txt

```

*(Nota: Nesta versão, como o Gemini processa as imagens de forma multimodal, a instalação e configuração do Tesseract OCR no Windows não são mais estritamente necessárias para a precisão do texto, embora o módulo base ainda faça parte da estrutura do projeto).*

---

*Projeto desenvolvido para fins acadêmicos.*
