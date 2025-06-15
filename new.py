import sys
import os
import json
import speech_recognition as sr
from gtts import gTTS
import datetime
import webbrowser
import requests
import tempfile
import pygame
import re
import yt_dlp
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                            QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, 
                            QScrollArea, QFileDialog, QMessageBox, QTabWidget)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor, QPalette

class DarkTheme:
    @staticmethod
    def apply(app):
        # Define a paleta de cores para o modo escuro
        dark_palette = QPalette()
        
        # Cores base
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
        dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
        
        app.setPalette(dark_palette)
        app.setStyle("Fusion")
        
        # Estilo adicional para melhorar a aparência
        app.setStyleSheet("""
            QGroupBox {
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            
            QTextEdit, QLineEdit {
                background-color: #252525;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                selection-background-color: #3d8ec9;
            }
            
            QPushButton {
                background-color: #555;
                border: none;
                border-radius: 3px;
                padding: 5px 10px;
                min-width: 80px;
            }
            
            QPushButton:hover {
                background-color: #666;
            }
            
            QPushButton:pressed {
                background-color: #444;
            }
            
            QPushButton:disabled {
                background-color: #333;
                color: #777;
            }
            
            QTabWidget::pane {
                border: 1px solid #555;
                top: -1px;
            }
            
            QTabBar::tab {
                background: #444;
                border: 1px solid #555;
                padding: 5px 10px;
            }
            
            QTabBar::tab:selected {
                background: #555;
                border-bottom-color: #3d8ec9;
            }
            
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
            
            QScrollBar:vertical {
                background: #353535;
                width: 12px;
                margin: 0px 0px 0px 0px;
            }
            
            QScrollBar::handle:vertical {
                background: #555;
                min-height: 20px;
            }
            
            QScrollBar::add-line:vertical {
                background: #353535;
                height: 0px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }
            
            QScrollBar::sub-line:vertical {
                background: #353535;
                height: 0px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }
        """)

class VoiceAssistantThread(QThread):
    command_received = pyqtSignal(str)
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_keys, parent=None):
        super().__init__(parent)
        self.api_keys = api_keys
        self.running = True
        self.modulo_musica = False
        self.musica_pausada = False
        
    def run(self):
        try:
            while self.running:
                comando = self.ouvir_comando()
                if comando:
                    self.command_received.emit(comando)
                    
                    if self.modulo_musica:
                        if "pausar música" in comando:
                            pygame.mixer.music.pause()
                            self.musica_pausada = True
                            self.response_ready.emit("Música pausada. Pode dar qualquer comando agora.")
                            self.modulo_musica = False
                        else:
                            self.response_ready.emit("Estou no modo música. Diga 'pausar música' para pausar.")
                        continue

                    if "continua música" in comando:
                        if self.musica_pausada:
                            pygame.mixer.music.unpause()
                            self.musica_pausada = False
                            self.modulo_musica = True
                            self.response_ready.emit("Música retomada. Só vou aceitar 'pausar música' agora.")
                        else:
                            self.response_ready.emit("Não tem música pausada para continuar.")
                        continue

                    if comando.startswith("luma"):
                        comando_limpo = comando.replace("luma", "", 1).strip()
                        self.response_ready.emit("Olá")

                        if any(x in comando_limpo for x in ["gera um texto", "gere um texto", "me fale", "quem nasceu", "explique", "conte", "como", "o que é", "qual é a", "abaixa o volume"]):
                            resposta = self.chamar_gemini(comando_limpo)
                            resposta_limpa = self.limpar_formatacao_markdown(resposta)
                            self.response_ready.emit(resposta_limpa)
                        elif comando_limpo:
                            self.executar_comando(comando_limpo)
                        else:
                            self.response_ready.emit("Pode falar o comando depois de me chamar.")
        except Exception as e:
            self.error_occurred.emit(f"Erro no assistente: {str(e)}")

    def ouvir_comando(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=2)
            audio = r.listen(source)
        try:
            comando = r.recognize_google(audio, language='pt-BR').lower()
            return comando
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            self.error_occurred.emit(f"Erro no serviço de reconhecimento de voz: {e}")
            return ""

    def limpar_formatacao_markdown(self, texto):
        texto = re.sub(r'(\*\*|__)(.*?)\1', r'\2', texto)
        texto = re.sub(r'(\*|_)(.*?)\1', r'\2', texto)
        texto = re.sub(r'`(.*?)`', r'\1', texto)
        return texto

    def falar(self, texto):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tf:
                tts = gTTS(text=texto, lang='pt-br', slow=False)
                tts.save(tf.name)
                temp_path = tf.name

            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.delay(100)

            pygame.mixer.music.unload()
            os.remove(temp_path)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao falar: {e}")

    def chamar_gemini(self, pergunta):
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [
                {
                    "parts": [{"text": pergunta}]
                }
            ]
        }
        try:
            resposta = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_keys['gemini']}",
                headers=headers,
                data=json.dumps(data)
            )
            resposta_json = resposta.json()
            texto_resp = resposta_json['candidates'][0]['content']['parts'][0]['text']
            return texto_resp
        except Exception as e:
            self.error_occurred.emit(f"Erro ao chamar Gemini: {e}")
            return "Desculpe, não consegui obter resposta do Gemini."

    def obter_previsao_tempo(self, cidade):
        params = {
            "q": cidade,
            "appid": self.api_keys['weather'],
            "lang": "pt_br",
            "units": "metric"
        }
        try:
            resposta = requests.get("http://api.openweathermap.org/data/2.5/weather", params=params)
            dados = resposta.json()
            if resposta.status_code == 200:
                descricao = dados["weather"][0]["description"]
                temperatura = dados["main"]["temp"]
                return f"Em {cidade}, está {descricao} com temperatura de {temperatura} graus."
            else:
                return f"Não consegui obter a previsão para {cidade}."
        except Exception as e:
            self.error_occurred.emit(f"Erro ao buscar o clima: {e}")
            return "Erro ao buscar o clima."

    def tocar_musica_youtube(self, pesquisa):
        try:
            nome_desejado = "musica.mp3"
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'quiet': True,
                'default_search': 'ytsearch1',
                'extract_flat': False,
                'outtmpl': 'audio_temp.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(pesquisa, download=True)
                titulo = info.get('title', pesquisa)

            if os.path.exists("musica.mp3"):
                os.remove("musica.mp3")

            os.rename("audio_temp.mp3", nome_desejado)

            self.response_ready.emit(f"Tocando {titulo}")
            pygame.mixer.music.load(nome_desejado)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.delay(100)

            pygame.mixer.music.unload()
            os.remove(nome_desejado)
        except Exception as e:
            self.error_occurred.emit(f"Erro ao tocar música: {e}")
            self.response_ready.emit("Erro ao tentar tocar a música.")

    def executar_comando(self, comando):
        if "são que horas" in comando:
            hora = datetime.datetime.now().strftime("%H:%M")
            self.response_ready.emit(f"Agora são {hora}")
            self.falar(f"Agora são {hora}")
        elif "qual a data de hoje" in comando:
            data = datetime.datetime.now().strftime("%d/%m/%Y")
            self.response_ready.emit(f"Hoje é {data}")
            self.falar(f"Hoje é {data}")
        elif "me diga as notícias de hoje" in comando:
            try:
                url = "https://g1.globo.com/"
                r = requests.get(url)
                soup = BeautifulSoup(r.text, 'html.parser')
                manchetes = soup.find_all('a', class_='feed-post-link', limit=5)

                if not manchetes:
                    self.response_ready.emit("Desculpe, não consegui encontrar notícias agora.")
                    self.falar("Desculpe, não consegui encontrar notícias agora.")
                else:
                    self.response_ready.emit("Estas são as principais notícias de hoje:")
                    self.falar("Estas são as principais notícias de hoje:")
                    for m in manchetes:
                        titulo = m.get_text(strip=True)
                        self.response_ready.emit("- " + titulo)
                        self.falar(titulo)
            except Exception as e:
                self.error_occurred.emit(f"Erro ao buscar notícias: {e}")
                self.response_ready.emit("Ocorreu um erro ao tentar buscar as notícias.")
                self.falar("Ocorreu um erro ao tentar buscar as notícias.")
        elif "abrir youtube" in comando:
            webbrowser.open("https://youtube.com")
            self.response_ready.emit("Abrindo o YouTube")
            self.falar("Abrindo o YouTube")
        elif "abrir github" in comando:
            webbrowser.open("https://github.com")
            self.response_ready.emit("abrindo github")
            self.falar("abrindo github")
        elif "abrir instagram" in comando:
            webbrowser.open("https://instagram.com")
            self.response_ready.emit("abrindo instagram")
            self.falar("abrindo instagram")
        elif "abrir google" in comando:
            webbrowser.open("https://google.com")
            self.response_ready.emit("Abrindo o Google")
            self.falar("Abrindo o Google")
        elif comando.startswith("toca ") or comando.startswith("tocar "):
            musica = comando.replace("toca ", "").replace("tocar ", "").strip()
            self.tocar_musica_youtube(musica)
        elif "qual é o seu nome" in comando:
            self.response_ready.emit("Meu nome é Luma, sua assistente pessoal.")
            self.falar("Meu nome é Luma, sua assistente pessoal.")
        elif "previsão" in comando or "clima" in comando or "tempo" in comando:
            palavras = comando.split()
            if "em" in palavras:
                indice = palavras.index("em")
                cidade = " ".join(palavras[indice + 1:])
                clima = self.obter_previsao_tempo(cidade)
                self.response_ready.emit(clima)
                self.falar(clima)
            else:
                self.response_ready.emit("Por favor, diga o nome da cidade. Exemplo: clima em São Paulo.")
                self.falar("Por favor, diga o nome da cidade. Exemplo: clima em São Paulo.")
        elif "parar" in comando:
            pygame.mixer.music.stop()
            self.response_ready.emit("Fala interrompida.")
        elif "sair" in comando or "fechar" in comando:
            self.response_ready.emit("Encerrando. Até mais!")
            self.falar("Encerrando. Até mais!")
            self.running = False
        else:
            self.response_ready.emit("Desculpe, não entendi esse comando.")
            self.falar("Desculpe, não entendi esse comando.")

    def stop(self):
        self.running = False
        self.wait()

class CustomCommandsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        group = QGroupBox("Adicionar Novo Comando")
        form_layout = QVBoxLayout()
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Comando de voz (ex: 'pesquisar no google')")
        
        self.action_input = QTextEdit()
        self.action_input.setPlaceholderText("Ação em Python (ex: webbrowser.open('https://google.com/search?q=' + termo))")
        
        self.add_button = QPushButton("Adicionar Comando")
        self.add_button.clicked.connect(self.add_custom_command)
        
        form_layout.addWidget(QLabel("Comando de Voz:"))
        form_layout.addWidget(self.command_input)
        form_layout.addWidget(QLabel("Ação Python:"))
        form_layout.addWidget(self.action_input)
        form_layout.addWidget(self.add_button)
        group.setLayout(form_layout)
        
        self.commands_list = QTextEdit()
        self.commands_list.setReadOnly(True)
        self.commands_list.setPlaceholderText("Seus comandos personalizados aparecerão aqui...")
        
        button_layout = QHBoxLayout()
        self.load_button = QPushButton("Carregar Comandos")
        self.load_button.clicked.connect(self.load_commands)
        self.save_button = QPushButton("Salvar Comandos")
        self.save_button.clicked.connect(self.save_commands)
        
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.save_button)
        
        layout.addWidget(group)
        layout.addWidget(QLabel("Comandos Personalizados:"))
        layout.addWidget(self.commands_list)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def add_custom_command(self):
        command = self.command_input.text().strip().lower()
        action = self.action_input.toPlainText().strip()
        
        if not command or not action:
            QMessageBox.warning(self, "Aviso", "Por favor, preencha ambos os campos!")
            return
            
        try:
            compile(action, '<string>', 'exec')
        except SyntaxError as e:
            QMessageBox.warning(self, "Erro de Sintaxe", f"O código Python contém erros:\n{str(e)}")
            return
            
        if hasattr(self.parent, 'assistant_thread'):
            self.parent.custom_commands[command] = action
            self.update_commands_list()
            QMessageBox.information(self, "Sucesso", "Comando adicionado com sucesso!")
            self.command_input.clear()
            self.action_input.clear()
        else:
            QMessageBox.warning(self, "Erro", "Assistente não inicializado!")
            
    def update_commands_list(self):
        if hasattr(self.parent, 'custom_commands'):
            text = ""
            for cmd, action in self.parent.custom_commands.items():
                text += f"Comando: {cmd}\nAção: {action}\n{'='*50}\n"
            self.commands_list.setPlainText(text)
            
    def save_commands(self):
        if hasattr(self.parent, 'custom_commands') and self.parent.custom_commands:
            file_path, _ = QFileDialog.getSaveFileName(self, "Salvar Comandos", "", "JSON Files (*.json)")
            if file_path:
                try:
                    with open(file_path, 'w') as f:
                        json.dump(self.parent.custom_commands, f, indent=4)
                    QMessageBox.information(self, "Sucesso", "Comandos salvos com sucesso!")
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Falha ao salvar comandos:\n{str(e)}")
        else:
            QMessageBox.warning(self, "Aviso", "Nenhum comando personalizado para salvar!")
            
    def load_commands(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Carregar Comandos", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    loaded_commands = json.load(f)
                self.parent.custom_commands.update(loaded_commands)
                self.update_commands_list()
                QMessageBox.information(self, "Sucesso", "Comandos carregados com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao carregar comandos:\n{str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        pygame.mixer.init()
        self.setWindowTitle("Luma - Assistente Virtual")
        self.setGeometry(100, 100, 900, 700)
        
        # Configuração de fonte
        self.font = QFont()
        self.font.setFamily("Segoe UI")
        self.font.setPointSize(10)
        QApplication.setFont(self.font)
        
        self.api_keys = {
            'gemini': '',
            'weather': ''
        }
        self.custom_commands = {}
        
        self.initUI()
        self.load_settings()
        
    def initUI(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Configuração da paleta de cores
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)
        
        api_group = QGroupBox("Configurações da API")
        api_layout = QVBoxLayout()
        
        gemini_layout = QHBoxLayout()
        gemini_layout.addWidget(QLabel("Gemini API Key:"))
        self.gemini_api_input = QLineEdit()
        self.gemini_api_input.setPlaceholderText("Insira sua chave Gemini API")
        self.gemini_api_input.setEchoMode(QLineEdit.Password)
        gemini_layout.addWidget(self.gemini_api_input)
        
        weather_layout = QHBoxLayout()
        weather_layout.addWidget(QLabel("Weather API Key:"))
        self.weather_api_input = QLineEdit()
        self.weather_api_input.setPlaceholderText("Insira sua chave OpenWeatherMap API")
        self.weather_api_input.setEchoMode(QLineEdit.Password)
        weather_layout.addWidget(self.weather_api_input)
        
        self.save_button = QPushButton("Salvar Configurações")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #3d8ec9;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4a9bdf;
            }
            QPushButton:pressed {
                background-color: #2d7cb7;
            }
        """)
        
        api_layout.addLayout(gemini_layout)
        api_layout.addLayout(weather_layout)
        api_layout.addWidget(self.save_button)
        api_group.setLayout(api_layout)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Log de atividades aparecerá aqui...")
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #252525;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
        """)
        
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("Iniciar Assistente")
        self.start_button.clicked.connect(self.start_assistant)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5CBF60;
            }
            QPushButton:pressed {
                background-color: #3C9F40;
            }
            QPushButton:disabled {
                background-color: #2E7D32;
                color: #AAA;
            }
        """)
        
        self.stop_button = QPushButton("Parar Assistente")
        self.stop_button.clicked.connect(self.stop_assistant)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #FF5346;
            }
            QPushButton:pressed {
                background-color: #D43326;
            }
            QPushButton:disabled {
                background-color: #B32B20;
                color: #AAA;
            }
        """)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #555;
                top: -1px;
                background: #353535;
            }
            
            QTabBar::tab {
                background: #444;
                border: 1px solid #555;
                padding: 8px 12px;
                color: white;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            
            QTabBar::tab:selected {
                background: #555;
                border-bottom-color: #3d8ec9;
            }
            
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
        """)
        
        self.tabs.addTab(self.create_main_tab(), "Principal")
        self.tabs.addTab(CustomCommandsTab(self), "Comandos Personalizados")
        
        main_layout.addWidget(api_group)
        main_layout.addWidget(self.tabs)
        main_layout.addWidget(QLabel("Log de Atividades:"))
        main_layout.addWidget(self.log_area)
        main_layout.addLayout(control_layout)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
    def create_main_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        instructions_label = QLabel(
                   "<h3 style='color:#3d8ec9'>Instruções de Uso:</h3>"
                   "<ol>"
                   "<li>Insira suas chaves de API</li>"
                   "<li>Clique em 'Salvar Configurações'</li>"
                   "<li>Clique em 'Iniciar Assistente'</li>"
                   "<li>Diga 'Luma' seguido do comando</li>"
                   "</ol>"                   "<p><b>Links para obter chaves de API:</b></p>"
                   "<ul>"
                   "<li><a href='https://aistudio.google.com/app/apikey' style='color:#3d8ec9'>Gemini API Key</a></li>"
                   "<li><a href='https://openweathermap.org/api' style='color:#3d8ec9'>OpenWeather API Key</a></li>"                   "</ul>"
                   "<h3 style='color:#3d8ec9'>Comandos Disponíveis:</h3>"
                   "<ul>"
                   "<li><b>São que horas</b> ou <b>qual a data de hoje</b></li>"
                   "<li><b>Me diga as notícias de hoje</b></li>"
                   "<li><b>Tocar + nome da música</b> (ex: Tocar Eminem)</li>"
                   "<li><b>Abrir youtube, github, instagram ou google</b></li>"
                   "<li><b>Previsão do Tempo</b> (ex: Clima em Rio de Janeiro)</li>"
                   "<li><b>Qual é o seu nome</b></li>"
                   "<li><b>Perguntas gerais</b> (via Gemini)</li>"
                   "<li><b>Parar</b> (Parar de Falar)</li>"
                   "<li><b>Pausar</b> ou <b>continua música</b></li>"
                   "<li><b>Sair</b> ou <b>Fechar</b> (Para Desativar a Luma)</li>"
                   "</ul>"
         )
        instructions_label.setWordWrap(True)
        instructions_label.setOpenExternalLinks(True)
        instructions_label.setStyleSheet("""
        QLabel {
        background-color: #252525;
        border-radius: 5px;
        padding: 15px;
        color: #DDD;
        }
        QLabel a {
        color: #3d8ec9;
        text-decoration: none;
        }
        """)

        scroll_area = QScrollArea()
        scroll_area.setWidget(instructions_label)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(300)  # Ajusta esse valor se quiser mais/menos altura
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        layout.addWidget(scroll_area)
        tab.setLayout(layout)
        return tab
        
    def save_settings(self):
        self.api_keys['gemini'] = self.gemini_api_input.text().strip()
        self.api_keys['weather'] = self.weather_api_input.text().strip()
        
        if not self.api_keys['gemini'] or not self.api_keys['weather']:
            QMessageBox.warning(self, "Aviso", "Por favor, insira ambas as chaves de API!")
            return
            
        try:
            with open('config.json', 'w') as f:
                json.dump(self.api_keys, f)
            self.log("Configurações salvas com sucesso!")
            
            # Mostrar mensagem de sucesso com estilo
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Sucesso")
            msg.setText("Configurações salvas com sucesso!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #353535;
                }
                QLabel {
                    color: white;
                }
            """)
            msg.exec_()
        except Exception as e:
            self.log(f"Erro ao salvar configurações: {str(e)}")
            
            # Mostrar mensagem de erro com estilo
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Erro")
            msg.setText(f"Falha ao salvar configurações:\n{str(e)}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #353535;
                }
                QLabel {
                    color: white;
                }
            """)
            msg.exec_()
            
    def load_settings(self):
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    self.api_keys = json.load(f)
                self.gemini_api_input.setText(self.api_keys['gemini'])
                self.weather_api_input.setText(self.api_keys['weather'])
                self.log("Configurações carregadas com sucesso!")
        except Exception as e:
            self.log(f"Erro ao carregar configurações: {str(e)}")
            
    def start_assistant(self):
        if not self.api_keys['gemini'] or not self.api_keys['weather']:
            QMessageBox.warning(self, "Aviso", "Por favor, configure e salve as chaves de API primeiro!")
            return
            
        self.assistant_thread = VoiceAssistantThread(self.api_keys)
        self.assistant_thread.command_received.connect(self.log_command)
        self.assistant_thread.response_ready.connect(self.log_response)
        self.assistant_thread.error_occurred.connect(self.log_error)
        self.assistant_thread.start()
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.log("Assistente iniciado. Diga 'Luma' seguido do comando.")
        
    def stop_assistant(self):
        if hasattr(self, 'assistant_thread'):
            self.assistant_thread.stop()
            self.assistant_thread.wait()
            del self.assistant_thread
            
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.log("Assistente parado.")
        
    def log(self, message):
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_area.append(f"[{timestamp}] {message}")
        
    def log_command(self, command):
        self.log(f"<span style='color:#4CAF50'>Comando recebido: {command}</span>")
        
    def log_response(self, response):
        self.log(f"<span style='color:#2196F3'>Resposta: {response}</span>")
        
    def log_error(self, error):
        self.log(f"<span style='color:#F44336'>ERRO: {error}</span>")
        
    def closeEvent(self, event):
     if hasattr(self, 'assistant_thread'):
        self.assistant_thread.running = False
        self.assistant_thread.wait(2000)  # espera no máximo 2 segundos
        pygame.mixer.quit()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Aplicar o tema escuro
    DarkTheme.apply(app)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())