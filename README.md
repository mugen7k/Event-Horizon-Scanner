# 📸 Scanner IA Pro

Um aplicativo de desktop moderno em Python que transforma sua webcam em um scanner de documentos inteligente. Utiliza Visão Computacional para detecção automática de bordas e a Inteligência Artificial do Google Gemini para correção e tradução de textos extraídos por OCR.

## ✨ Funcionalidades

*   **Detecção Automática (CamScanner Style):** Reconhece as bordas do papel em tempo real e realiza o recorte com correção de perspectiva (Warp Perspective).
*   **OCR Avançado:** Extração de texto a partir da imagem binarizada usando Tesseract e filtros adaptativos do OpenCV.
*   **Processamento com IA (Google Gemini 2.5 Flash):** O texto cru do OCR é enviado para a IA corrigir pontuações fantasmas, quebras de linha e formatar o parágrafo perfeitamente.
*   **Tradução Integrada:** Opção de traduzir o texto escaneado automaticamente para Inglês ou Espanhol.
*   **Text-to-Speech (TTS):** Geração de áudio narrado (.mp3) do documento na língua selecionada.
*   **Exportação:** Salva os resultados automaticamente em um documento PDF formatado.
*   **Interface Gráfica:** UI moderna e responsiva construída com CustomTkinter (Modo Escuro).

## 🛠️ Tecnologias Utilizadas

*   **Python 3.x**
*   **OpenCV & NumPy** (Processamento de Imagem)
*   **Pytesseract** (Reconhecimento Óptico de Caracteres)
*   **Google GenAI SDK** (Integração com Gemini LLM)
*   **CustomTkinter** (Interface Gráfica)
*   **gTTS & FPDF** (Exportação de Áudio e PDF)

## 🚀 Como instalar e rodar

### 1. Pré-requisitos
*   Python instalado na sua máquina.
*   Para rodar este projeto, você precisará de uma API Key do Gemini.
*   [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) instalado no seu sistema operacional.
    *   *Nota para Windows:* Certifique-se de que o caminho do Tesseract esteja correto no código ou adicionado ao PATH do Windows.

#
*Projeto desenvolvido para fins acadêmicos.*