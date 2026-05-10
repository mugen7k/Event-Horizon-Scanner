import cv2
import numpy as np
import pytesseract
import customtkinter as ctk
from PIL import Image
from google import genai
from gtts import gTTS
import os
import threading
from fpdf import FPDF

CHAVE_API = ""

if CHAVE_API == "":
    print("⚠️ ATENÇÃO: Você esqueceu de inserir sua CHAVE_API na linha 12 do código!")

cliente_ia = genai.Client(api_key=CHAVE_API)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def ordenar_pontos(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def transformar_perspectiva(imagem, pts):
    rect = ordenar_pontos(pts)
    (tl, tr, br, bl) = rect

    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))

    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b))

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")

    matriz_transformacao = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(imagem, matriz_transformacao, (max_width, max_height))
    return warped


class AppScanner(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Scanner IA Pro")
        self.geometry("1100x650")
        self.protocol("WM_DELETE_WINDOW", self.fechar_app)

        self.processando = False
        self.contorno_documento = None
        self.texto_final = ""

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.painel_video = ctk.CTkLabel(self, text="")
        self.painel_video.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.frame_controles = ctk.CTkFrame(self)
        self.frame_controles.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        ctk.CTkLabel(self.frame_controles, text="Modo de Inteligência Artificial:", font=("Arial", 14, "bold")).pack(
            pady=(20, 5))
        self.combo_ia = ctk.CTkComboBox(self.frame_controles, values=["Apenas Corrigir (PT-BR)", "Traduzir para Inglês",
                                                                      "Traduzir para Espanhol"])
        self.combo_ia.pack(pady=5, padx=20, fill="x")

        self.btn_capturar = ctk.CTkButton(self.frame_controles, text="📸 CAPTURAR DOCUMENTO", height=50,
                                          font=("Arial", 16, "bold"), command=self.iniciar_captura)
        self.btn_capturar.pack(pady=20, padx=20, fill="x")

        self.caixa_texto = ctk.CTkTextbox(self.frame_controles, font=("Arial", 14))
        self.caixa_texto.pack(pady=10, padx=20, fill="both", expand=True)
        self.caixa_texto.insert("0.0", "O texto escaneado e processado aparecerá aqui...")

        self.frame_botoes = ctk.CTkFrame(self.frame_controles, fg_color="transparent")
        self.frame_botoes.pack(pady=20, padx=20, fill="x")

        self.btn_pdf = ctk.CTkButton(self.frame_botoes, text="Salvar PDF", state="disabled", command=self.salvar_pdf)
        self.btn_pdf.pack(side="left", padx=5, expand=True, fill="x")

        self.btn_audio = ctk.CTkButton(self.frame_botoes, text="Ouvir Áudio", state="disabled",
                                       command=self.gerar_audio)
        self.btn_audio.pack(side="right", padx=5, expand=True, fill="x")

        self.cap = cv2.VideoCapture(0)
        self.atualizar_camera()

    def atualizar_camera(self):
        if not self.processando and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                suavizado = cv2.GaussianBlur(cinza, (5, 5), 0)
                bordas = cv2.Canny(suavizado, 75, 200)

                contornos, _ = cv2.findContours(bordas, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
                contornos = sorted(contornos, key=cv2.contourArea, reverse=True)[:5]

                self.contorno_documento = None
                for c in contornos:
                    perimetro = cv2.arcLength(c, True)
                    aproximacao = cv2.approxPolyDP(c, 0.02 * perimetro, True)
                    if len(aproximacao) == 4 and cv2.contourArea(aproximacao) > 10000:
                        self.contorno_documento = aproximacao
                        cv2.drawContours(frame, [self.contorno_documento], -1, (0, 255, 0), 3)
                        break

                imagem_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                imagem_pil = Image.fromarray(imagem_rgb)
                imgtk = ctk.CTkImage(light_image=imagem_pil, dark_image=imagem_pil, size=(500, 375))

                self.painel_video.configure(image=imgtk)
                self.painel_video.image = imgtk

        self.after(15, self.atualizar_camera)

    def iniciar_captura(self):
        if not self.cap.isOpened(): return

        self.processando = True
        self.btn_capturar.configure(text="⏳ Processando IA...", state="disabled")
        self.caixa_texto.delete("0.0", "end")
        self.caixa_texto.insert("0.0",
                                "1. Recortando e limpando imagem...\n2. Lendo texto (OCR)...\n3. Conectando com a IA para formatação/tradução...\n\nPor favor, aguarde.")

        ret, frame = self.cap.read()
        if ret:
            threading.Thread(target=lambda: self.processar_imagem_ia(frame)).start()

    def processar_imagem_ia(self, frame):
        try:
            if self.contorno_documento is not None:
                imagem_cortada = transformar_perspectiva(frame, self.contorno_documento.reshape(4, 2))
            else:
                imagem_cortada = frame

            cinza = cv2.cvtColor(imagem_cortada, cv2.COLOR_BGR2GRAY)
            suavizada = cv2.GaussianBlur(cinza, (7, 7), 0)
            imagem_limpa = cv2.adaptiveThreshold(suavizada, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 19,
                                                 10)

            texto_bruto = pytesseract.image_to_string(imagem_limpa, lang='por', config='--psm 6')

            if not texto_bruto.strip():
                self.atualizar_ui("Erro: Nenhum texto encontrado na imagem. Tente melhorar a luz ou o foco.")
                return

            modo_ia = self.combo_ia.get()

            instrucao = f"Corrija este texto extraído por OCR, arrumando a pontuação e formatação."
            if "Inglês" in modo_ia:
                instrucao += " Em seguida, traduza perfeitamente para o INGLÊS."
            elif "Espanhol" in modo_ia:
                instrucao += " Em seguida, traduza perfeitamente para o ESPANHOL."
            instrucao += f"\n\nRetorne APENAS o texto final pronto.\n\nTexto Bruto:\n{texto_bruto}"

            nome_do_modelo = 'gemini-2.5-flash'

            resposta = cliente_ia.models.generate_content(
                model=nome_do_modelo,
                contents=instrucao
            )

            self.texto_final = resposta.text.strip()
            self.atualizar_ui(self.texto_final, sucesso=True)

        except Exception as e:
            self.atualizar_ui(f"Erro no processamento da IA: {e}")

    def atualizar_ui(self, texto, sucesso=False):
        self.caixa_texto.delete("0.0", "end")
        self.caixa_texto.insert("0.0", texto)

        self.btn_capturar.configure(text="📸 NOVA CAPTURA", state="normal")
        self.processando = False

        if sucesso:
            self.btn_pdf.configure(state="normal")
            self.btn_audio.configure(state="normal")
        else:
            self.btn_pdf.configure(state="disabled")
            self.btn_audio.configure(state="disabled")

    def salvar_pdf(self):
        if not self.texto_final: return

        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)

            texto_limpo = self.texto_final.encode('latin-1', 'replace').decode('latin-1')

            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="Documento Digitalizado - Scanner IA", ln=True, align='C')
            pdf.ln(10)

            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, txt=texto_limpo)

            nome_arquivo = "Documento_Escaneado.pdf"
            pdf.output(nome_arquivo)
            os.startfile(nome_arquivo)
        except Exception as e:
            print(f"Erro ao salvar PDF: {e}")

    def gerar_audio(self):
        if not self.texto_final: return

        self.btn_audio.configure(text="Gerando...", state="disabled")
        try:
            idioma = 'pt'
            if "Inglês" in self.combo_ia.get():
                idioma = 'en'
            elif "Espanhol" in self.combo_ia.get():
                idioma = 'es'

            tts = gTTS(text=self.texto_final, lang=idioma, slow=False)
            tts.save("Leitura.mp3")
            os.startfile("Leitura.mp3")
        except Exception as e:
            print(f"Erro ao gerar áudio: {e}")
        finally:
            self.btn_audio.configure(text="Ouvir Áudio", state="normal")

    def fechar_app(self):
        if self.cap.isOpened():
            self.cap.release()
        self.destroy()


if __name__ == "__main__":
    app = AppScanner()
    app.mainloop()