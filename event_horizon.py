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
import tkinter as tk

CHAVE_API = ""

if CHAVE_API == "":
    print("⚠️ ATENÇÃO: Você esqueceu de inserir sua CHAVE_API na linha 13 do código!")
    cliente_ia = None
else:
    cliente_ia = genai.Client(api_key=CHAVE_API)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

ctk.set_appearance_mode("light")

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
        self.geometry("450x820")
        self.protocol("WM_DELETE_WINDOW", self.fechar_app)

        self.configure(fg_color="#F2F2F7")

        self.processando = False
        self.contorno_documento = None
        self.texto_final = ""
        self.historico_capturas = []
        self.angulo_spinner = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self.header = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=0, height=70)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)
        self.header.grid_columnconfigure(0, weight=1)
        self.header.grid_rowconfigure(0, weight=1)

        try:
            diretorio_atual = os.path.dirname(os.path.abspath(__file__))
            caminho_logo = os.path.join(diretorio_atual, "EVENT HORIZON - LOGOTIPO TRANSPARENTE.png")
            imagem_logo = Image.open(caminho_logo)
            largura_original, altura_original = imagem_logo.size
            altura_desejada = 150
            proporcao = altura_desejada / altura_original
            largura_desejada = int(largura_original * proporcao)

            self.logo_img = ctk.CTkImage(light_image=imagem_logo, dark_image=imagem_logo,
                                         size=(largura_desejada, altura_desejada))
            ctk.CTkLabel(self.header, text="", image=self.logo_img).grid(row=0, column=0, padx=15, sticky="w")
        except Exception as e:
            print(f"Aviso: Logotipo não encontrado ({e}). Exibindo texto padrão.")
            ctk.CTkLabel(self.header, text="Event Horizon", font=("Helvetica", 20, "bold"), text_color="#000000").grid(
                row=0, column=0, padx=15, sticky="w")

        self.btn_sair = ctk.CTkButton(
            self.header, text="Sair", width=60, height=30, corner_radius=10,
            fg_color="#333333", hover_color="#000000", text_color="#FFFFFF", font=("Helvetica", 12, "bold"),
            command=self.fechar_app
        )
        self.btn_sair.grid(row=0, column=1, padx=15, sticky="e")

        self.frame_camera = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_camera.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)

        self.painel_video = ctk.CTkLabel(self.frame_camera, text="")
        self.painel_video.pack(expand=True)

        self.frame_texto = ctk.CTkFrame(self, fg_color="transparent")
        self.caixa_texto = ctk.CTkTextbox(
            self.frame_texto, font=("Helvetica", 15),
            fg_color="#FFFFFF", text_color="#1D1D1F",
            border_width=2, border_color="#E5E5EA", corner_radius=15
        )
        self.caixa_texto.pack(fill="both", expand=True)

        self.frame_loading = ctk.CTkFrame(self, fg_color="transparent")

        self.canvas_spinner = tk.Canvas(
            self.frame_loading, width=90, height=90,
            bg="#F2F2F7", highlightthickness=0
        )
        self.canvas_spinner.pack(pady=(160, 20))

        self.label_loading = ctk.CTkLabel(
            self.frame_loading,
            text="✨ Analisando documento com IA...\nPor favor, aguarde alguns segundos.",
            font=("Helvetica", 15, "bold"),
            text_color="#1D1D1F",
            justify="center"
        )
        self.label_loading.pack(pady=10)

        self.frame_historico = ctk.CTkScrollableFrame(self, fg_color="transparent")

        self.painel_inferior = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=25, border_width=1,
                                            border_color="#E5E5EA")
        self.painel_inferior.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 20))

        self.controles_camera = ctk.CTkFrame(self.painel_inferior, fg_color="transparent")
        self.controles_camera.pack(fill="both", expand=True, pady=15)

        ctk.CTkLabel(self.controles_camera, text="⚙️ Processamento IA", font=("Helvetica", 12, "bold"),
                     text_color="#888888").pack(pady=(5, 5))

        self.modo_ia_var = ctk.StringVar(value="PT-BR")
        self.seletor_ia = ctk.CTkSegmentedButton(
            self.controles_camera,
            values=["PT-BR", "Inglês", "Espanhol"],
            variable=self.modo_ia_var,
            fg_color="#E5E5EA", selected_color="#FFC107", selected_hover_color="#FFD54F",
            unselected_color="#F2F2F7", unselected_hover_color="#FFFFFF", text_color="#000000",
            height=35, corner_radius=10
        )
        self.seletor_ia.pack(pady=10, padx=20, fill="x")

        self.btn_capturar = ctk.CTkButton(
            self.controles_camera, text="", width=75, height=75, corner_radius=40,
            fg_color="#FFC107", hover_color="#FFD54F", border_width=5, border_color="#FFE082",
            command=self.iniciar_captura
        )
        self.btn_capturar.pack(pady=(10, 5))

        self.btn_abrir_historico = ctk.CTkButton(
            self.controles_camera, text="📚 Ver Histórico", width=200, height=35, corner_radius=10,
            fg_color="#E5E5EA", text_color="#000000", hover_color="#D1D1D6", font=("Helvetica", 12, "bold"),
            command=self.abrir_historico
        )
        self.btn_abrir_historico.pack(pady=(10, 5))

        self.controles_resultado = ctk.CTkFrame(self.painel_inferior, fg_color="transparent")
        self.controles_resultado.grid_columnconfigure((0, 1), weight=1, uniform="colunas")

        cor_botao = "#FFC107"
        cor_hover = "#FFD54F"
        cor_texto_btn = "#000000"

        self.btn_pdf = ctk.CTkButton(self.controles_resultado, text="📄 Salvar PDF", width=100, height=45,
                                     corner_radius=10, fg_color=cor_botao, text_color=cor_texto_btn,
                                     hover_color=cor_hover, command=self.salvar_pdf)
        self.btn_audio = ctk.CTkButton(self.controles_resultado, text="🔊 Áudio Completo", width=100, height=45,
                                       corner_radius=10, fg_color=cor_botao, text_color=cor_texto_btn,
                                       hover_color=cor_hover, command=self.gerar_audio)
        self.btn_audio_resumo = ctk.CTkButton(self.controles_resultado, text="🎧 Áudio Resumido", width=100, height=45,
                                              corner_radius=10, fg_color=cor_botao, text_color=cor_texto_btn,
                                              hover_color=cor_hover, command=self.gerar_audio_resumo)
        self.btn_voltar = ctk.CTkButton(self.controles_resultado, text="📷 Tirar Outra", width=100, height=45,
                                        corner_radius=10, fg_color="#E5E5EA", text_color="#000000",
                                        hover_color="#D1D1D6", command=self.voltar_camera)

        self.btn_pdf.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.btn_audio.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.btn_audio_resumo.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.btn_voltar.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.cap = cv2.VideoCapture(0)
        self.atualizar_camera()

    def animar_spinner(self):
        if self.processando and hasattr(self, 'canvas_spinner') and self.frame_loading.winfo_ismapped():
            self.canvas_spinner.delete("arco")
            self.canvas_spinner.create_arc(
                10, 10, 80, 80,
                start=self.angulo_spinner,
                extent=110,
                style=tk.ARC,
                outline="#FFC107",
                width=7,
                tags="arco"
            )
            self.angulo_spinner = (self.angulo_spinner + 18) % 360
            self.after(30, self.animar_spinner)

    def abrir_historico(self):
        self.processando = True
        self.frame_camera.grid_forget()
        self.painel_inferior.grid_forget()

        self.frame_historico.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=15, pady=15)

        for widget in self.frame_historico.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.frame_historico, text="📚 Capturas Realizadas", font=("Helvetica", 18, "bold"),
                     text_color="#1D1D1F").pack(pady=10)
        ctk.CTkButton(self.frame_historico, text="Voltar para Câmera", fg_color="#E5E5EA", text_color="#000000",
                      hover_color="#D1D1D6", command=self.fechar_historico).pack(pady=(0, 15))

        if not self.historico_capturas:
            ctk.CTkLabel(self.frame_historico, text="Nenhum texto salvo ainda.", text_color="#888888").pack(pady=20)
        else:
            for item in reversed(self.historico_capturas):
                card = ctk.CTkFrame(self.frame_historico, fg_color="#FFFFFF", border_width=1, border_color="#E5E5EA",
                                    corner_radius=10)
                card.pack(fill="x", pady=5, padx=5)

                ctk.CTkLabel(card, text=f"Modo: {item['modo']}", font=("Helvetica", 12, "bold"),
                             text_color="#FFC107").pack(anchor="w", padx=10, pady=(5, 0))

                preview = item['texto'][:80].replace('\n', ' ') + "..."
                ctk.CTkLabel(card, text=preview, text_color="#1D1D1F", justify="left", wraplength=350).pack(anchor="w",
                                                                                                            padx=10,
                                                                                                            pady=(0, 5))

                btn_abrir = ctk.CTkButton(card, text="Abrir", width=80, height=30, fg_color="#FFC107",
                                          text_color="#000000", hover_color="#FFD54F",
                                          command=lambda t=item['texto']: self.visualizar_historico(t))
                btn_abrir.pack(anchor="e", padx=10, pady=10)

    def fechar_historico(self):
        self.frame_historico.grid_forget()
        self.frame_camera.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        self.painel_inferior.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 20))
        self.processando = False

    def visualizar_historico(self, texto):
        self.frame_historico.grid_forget()
        self.painel_inferior.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 20))
        self.controles_camera.pack_forget()
        self.frame_camera.grid_forget()
        self.frame_texto.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)

        self.texto_final = texto
        self.atualizar_ui(texto, sucesso=True)

    def _cortar_frame_vertical(self, frame):
        h, w, _ = frame.shape
        target_w = int(h * 9 / 16)
        start_x = (w - target_w) // 2
        return frame[:, start_x:start_x + target_w]

    def atualizar_camera(self):
        if not self.processando and self.cap.isOpened():
            ret, frame_bruto = self.cap.read()
            if ret:
                frame = self._cortar_frame_vertical(frame_bruto)
                cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                suavizado = cv2.GaussianBlur(cinza, (5, 5), 0)
                bordas = cv2.Canny(suavizado, 75, 200)
                contornos, _ = cv2.findContours(bordas, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
                contornos = sorted(contornos, key=cv2.contourArea, reverse=True)[:5]
                self.contorno_documento = None
                for c in contornos:
                    perimetro = cv2.arcLength(c, True)
                    aproximacao = cv2.approxPolyDP(c, 0.02 * perimetro, True)
                    if len(aproximacao) == 4 and cv2.contourArea(aproximacao) > 8000:
                        self.contorno_documento = aproximacao
                        cv2.drawContours(frame, [self.contorno_documento], -1, (0, 255, 0), 2)
                        break
                imagem_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                imagem_pil = Image.fromarray(imagem_rgb)
                imgtk = ctk.CTkImage(light_image=imagem_pil, dark_image=imagem_pil, size=(288, 512))
                self.painel_video.configure(image=imgtk)
                self.painel_video.image = imgtk
        self.after(15, self.atualizar_camera)

    def iniciar_captura(self):
        if not self.cap.isOpened(): return
        if not cliente_ia:
            print("Erro: Chave API ausente!")
            return

        self.processando = True
        self.controles_camera.pack_forget()
        self.frame_camera.grid_forget()

        self.frame_loading.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        self.angulo_spinner = 0
        self.animar_spinner()

        ret, frame_bruto = self.cap.read()
        if ret:
            frame_cortado = self._cortar_frame_vertical(frame_bruto)
            threading.Thread(target=lambda: self.processar_imagem_ia(frame_cortado)).start()

    def processar_imagem_ia(self, frame):
        try:
            if self.contorno_documento is not None:
                imagem_cortada = transformar_perspectiva(frame, self.contorno_documento.reshape(4, 2))
            else:
                imagem_cortada = frame

            imagem_rgb = cv2.cvtColor(imagem_cortada, cv2.COLOR_BGR2RGB)
            imagem_pil = Image.fromarray(imagem_rgb)

            modo_ia = self.modo_ia_var.get()

            instrucao = "Atue como um scanner de alta precisão. Extraia TODO o texto legível desta imagem com precisão absoluta, mantendo a formatação e corrigindo eventuais pontuações."
            if "Inglês" in modo_ia:
                instrucao += " Em seguida, retorne APENAS a tradução perfeita do texto para o INGLÊS. Não inclua o texto original nem comentários."
            elif "Espanhol" in modo_ia:
                instrucao += " Em seguida, retorne APENAS a tradução perfeita do texto para o ESPANHOL. Não inclua o texto original nem comentários."
            else:
                instrucao += " Retorne APENAS o texto extraído e bem formatado em PT-BR. Não adicione comentários extras."

            chat = cliente_ia.chats.create(model='gemini-2.5-flash')
            resposta = chat.send_message([instrucao, imagem_pil])

            self.texto_final = resposta.text.strip()

            self.historico_capturas.append({
                "modo": modo_ia,
                "texto": self.texto_final
            })

            self.atualizar_ui(self.texto_final, sucesso=True)

        except Exception as e:
            self.atualizar_ui(f"❌ Erro no processamento da IA: {e}")

    def atualizar_ui(self, texto, sucesso=False):
        self.frame_loading.grid_forget()
        self.frame_texto.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)

        self.caixa_texto.delete("0.0", "end")
        self.caixa_texto.insert("0.0", texto)
        self.controles_resultado.pack(fill="both", expand=True, pady=15, padx=10)

        if not sucesso:
            self.btn_pdf.configure(state="disabled")
            self.btn_audio.configure(state="disabled")
            self.btn_audio_resumo.configure(state="disabled")
        else:
            self.btn_pdf.configure(state="normal")
            self.btn_audio.configure(state="normal")
            self.btn_audio_resumo.configure(state="normal")

    def voltar_camera(self):
        self.controles_resultado.pack_forget()
        self.frame_texto.grid_forget()
        self.frame_camera.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        self.controles_camera.pack(fill="both", expand=True, pady=15)
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
        threading.Thread(target=self._processar_audio,
                         args=(self.texto_final, self.btn_audio, "🔊 Áudio Completo")).start()

    def gerar_audio_resumo(self):
        if not self.texto_final: return
        self.btn_audio_resumo.configure(text="⏳ Resumindo...", state="disabled")
        self.btn_audio.configure(state="disabled")
        threading.Thread(target=self._processar_resumo_e_audio).start()

    def _processar_resumo_e_audio(self):
        try:
            instrucao_resumo = f"Faça um resumo direto e fluido do seguinte texto para ser transformado em áudio. Mantenha o idioma atual do texto:\n\n{self.texto_final}"
            chat = cliente_ia.chats.create(model='gemini-2.5-flash')
            resposta = chat.send_message(instrucao_resumo)
            texto_resumido = resposta.text.strip()
            self.btn_audio_resumo.configure(text="⏳ Gerando...")
            self._processar_audio(texto_resumido, self.btn_audio_resumo, "🎧 Áudio Resumido")
        except Exception as e:
            print(f"Erro ao gerar resumo: {e}")
            self.btn_audio_resumo.configure(text="🎧 Áudio Resumido", state="normal")
            self.btn_audio.configure(state="normal")

    def _processar_audio(self, texto, botao, texto_original):
        try:
            idioma = self.modo_ia_var.get()
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
