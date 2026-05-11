import cv2
import numpy as np
import pytesseract
import customtkinter as ctk
from PIL import Image
from google import genai
import os
import threading
from fpdf import FPDF
import asyncio
import edge_tts

CHAVE_API = ""

if CHAVE_API == "":
    print("⚠️ ATENÇÃO: Você esqueceu de inserir sua CHAVE_API na linha 14 do código!")
    cliente_ia = None
else:
    cliente_ia = genai.Client(api_key=CHAVE_API)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

ctk.set_appearance_mode("dark")

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
        self.title("Event Horizon Scanner")
        self.geometry("550x850")
        self.protocol("WM_DELETE_WINDOW", self.fechar_app)
        self.configure(fg_color="#000000")
        self.processando = False
        self.contorno_documento = None
        self.texto_final = ""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.painel_video = ctk.CTkLabel(self, text="")
        self.painel_video.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.caixa_texto = ctk.CTkTextbox(
            self, font=("Arial", 16), fg_color="#111111",
            text_color="white", border_width=1, border_color="#333333"
        )
        self.painel_inferior = ctk.CTkFrame(self, fg_color="#000000")
        self.painel_inferior.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(self.painel_inferior, text="⚙️ MODO IA", font=("Arial", 12, "bold"), text_color="gray").pack(pady=(0, 5))
        self.combo_ia = ctk.CTkComboBox(
            self.painel_inferior,
            values=["Apenas Corrigir (PT-BR)", "Traduzir para Inglês", "Traduzir para Espanhol"],
            fg_color="#222222", border_color="#333333", dropdown_fg_color="#222222"
        )
        self.combo_ia.pack(pady=5, padx=20)
        self.btn_capturar = ctk.CTkButton(
            self.painel_inferior,
            text="",
            width=80, height=80, corner_radius=40,
            fg_color="white", hover_color="#e0e0e0",
            border_width=6, border_color="#333333",
            command=self.iniciar_captura
        )
        self.btn_capturar.pack(pady=20)
        self.btn_voltar = ctk.CTkButton(self.painel_inferior, text="📷 Tirar Outra Foto", fg_color="#333333", hover_color="#444444", command=self.voltar_camera)
        self.btn_pdf = ctk.CTkButton(self.painel_inferior, text="📄 Salvar PDF", command=self.salvar_pdf)
        self.btn_audio = ctk.CTkButton(self.painel_inferior, text="🔊 Áudio Completo", command=self.gerar_audio)
        self.btn_audio_resumo = ctk.CTkButton(self.painel_inferior, text="🎧 Áudio Resumido", command=self.gerar_audio_resumo)
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
                        cv2.drawContours(frame, [self.contorno_documento], -1, (0, 255, 0), 2)
                        break
                imagem_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                imagem_pil = Image.fromarray(imagem_rgb)
                imgtk = ctk.CTkImage(light_image=imagem_pil, dark_image=imagem_pil, size=(500, 375))
                self.painel_video.configure(image=imgtk)
                self.painel_video.image = imgtk
        self.after(15, self.atualizar_camera)

    def iniciar_captura(self):
        if not self.cap.isOpened(): return
        if not cliente_ia:
            print("Erro: Chave API ausente!")
            return
        self.processando = True
        self.painel_video.grid_forget()
        self.btn_capturar.pack_forget()
        self.caixa_texto.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.caixa_texto.delete("0.0", "end")
        self.caixa_texto.insert("0.0", "✨ Processando documento com IA...\nPor favor, aguarde alguns segundos.")
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
            imagem_limpa = cv2.adaptiveThreshold(suavizada, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 19, 10)
            texto_bruto = pytesseract.image_to_string(imagem_limpa, lang='por', config='--psm 6')
            if not texto_bruto.strip():
                self.atualizar_ui("❌ Erro: Nenhum texto encontrado na imagem. Volte e tente melhorar o foco.")
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
            self.atualizar_ui(f"❌ Erro no processamento da IA: {e}")

    def atualizar_ui(self, texto, sucesso=False):
        self.caixa_texto.delete("0.0", "end")
        self.caixa_texto.insert("0.0", texto)
        self.btn_voltar.pack(pady=5, fill="x", padx=40)
        if sucesso:
            self.btn_pdf.pack(pady=5, fill="x", padx=40)
            self.btn_audio.pack(pady=5, fill="x", padx=40)
            self.btn_audio_resumo.pack(pady=5, fill="x", padx=40)

    def voltar_camera(self):
        self.caixa_texto.grid_forget()
        self.btn_voltar.pack_forget()
        self.btn_pdf.pack_forget()
        self.btn_audio.pack_forget()
        self.btn_audio_resumo.pack_forget()
        self.painel_video.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.btn_capturar.pack(pady=20)
        self.processando = False

    def salvar_pdf(self):
        if not self.texto_final: return
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            texto_limpo = self.texto_final.encode('latin-1', 'replace').decode('latin-1')
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="Event Horizon - Documento Digitalizado", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, txt=texto_limpo)
            pdf.output("Documento_Escaneado.pdf")
            os.startfile("Documento_Escaneado.pdf")
        except Exception as e:
            print(f"Erro ao salvar PDF: {e}")

    def gerar_audio(self):
        if not self.texto_final: return
        self.btn_audio.configure(text="⏳ Gerando...", state="disabled")
        self.btn_audio_resumo.configure(state="disabled")
        threading.Thread(target=self._processar_audio, args=(self.texto_final, self.btn_audio, "🔊 Áudio Completo")).start()

    def gerar_audio_resumo(self):
        if not self.texto_final: return
        self.btn_audio_resumo.configure(text="⏳ Resumindo...", state="disabled")
        self.btn_audio.configure(state="disabled")
        threading.Thread(target=self._processar_resumo_e_audio).start()

    def _processar_resumo_e_audio(self):
        try:
            instrucao_resumo = f"Faça um resumo direto e fluido do seguinte texto para ser transformado em áudio. Mantenha o idioma atual do texto:\n\n{self.texto_final}"
            resposta = cliente_ia.models.generate_content(
                model='gemini-2.5-flash',
                contents=instrucao_resumo
            )
            texto_resumido = resposta.text.strip()
            self.btn_audio_resumo.configure(text="⏳ Gerando...")
            self._processar_audio(texto_resumido, self.btn_audio_resumo, "🎧 Áudio Resumido")
        except Exception as e:
            print(f"Erro ao gerar resumo: {e}")
            self.btn_audio_resumo.configure(text="🎧 Áudio Resumido", state="normal")
            self.btn_audio.configure(state="normal")

    def _processar_audio(self, texto, botao, texto_original):
        try:
            idioma = self.combo_ia.get()
            if "Inglês" in idioma:
                voz = "en-US-ChristopherNeural"
            elif "Espanhol" in idioma:
                voz = "es-ES-AlvaroNeural"
            else:
                voz = "pt-BR-FranciscaNeural"
            asyncio.run(self._gerar_arquivo_audio(texto, voz))
            os.startfile("Leitura.mp3")
        except Exception as e:
            print(f"Erro ao gerar áudio: {e}")
        finally:
            botao.configure(text=texto_original, state="normal")
            if botao == self.btn_audio:
                self.btn_audio_resumo.configure(state="normal")
            else:
                self.btn_audio.configure(state="normal")

    @staticmethod
    async def _gerar_arquivo_audio(texto, voz):
        comunicador = edge_tts.Communicate(texto, voz)
        await comunicador.save("Leitura.mp3")

    def fechar_app(self):
        if self.cap.isOpened():
            self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = AppScanner()
    app.mainloop()