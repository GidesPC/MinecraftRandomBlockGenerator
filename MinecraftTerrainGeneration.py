#[RU] максимально рекомендованная версия python - 3.10.x, выше придется заморачиваться с установкой amulet-core
#[EN] the maximum recommended version of python is 3.10.x, above that you will have to bother with installing amulet-core
import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import amulet
from amulet.api.block import Block
import random
import json
import sys
from datetime import datetime
import qdarktheme
from functools import partial
import time
import shutil
import requests
import subprocess


GITHUB_RELEASES = "https://api.github.com/repos/GidesPC/MinecraftRandomBlockGenerator/releases"
SETTINGS_FILE = "minecraft_terrain_generator_config.json"
current_version = "1.2(2025.07.07)"
game_versions = {
	"1.12.2":(1, 12, 2),
	"1.13":(1, 13, 0),
	"1.13.1-1.13.2":(1, 13, 1),
	"1.14.x":(1, 14,0),
	"1.15.x":(1, 15,0),
	"1.16.x":(1, 16,0),
	"1.17.x":(1, 17,0),
	"1.18.x":(1, 18,0),
	"1.19.x":(1, 19,0),
	"1.20.x":(1, 20,0),
	"1.21-1.21.3":(1, 21,0),
	"1.21.4":(1, 21, 4),
	"1.21.5":(1, 21,5),
	"1.21.6-1.21.7":(1, 21,6),
	
}

changelog_1_1_v = """
-Добавлен кнопка списка изменений
-Добавлен выбор версий (с 1.12.2 по 1.21.5 (версии ниже не поддерживает сама библиотека))
-Добавлен переключатель тем
-Адаптировано под маленькие экраны (не ниже 1024х768)
-Добавлена возможность обновлений
-Добавлен минимальный конфиг, а именно:
1)Возможность включать/отключать создание лог файлов после генерации
2)Сохранение 5 последних миров, в которых была произведена генерация
3)Сохранение установленной темы
4)Включение и отключение автообновлений
"""

changelog_1_2_v = """
-Добавлена поддержка версий 1.21.6-1.21.7
"""

changelogs = {
	"Версия 1.1(2025.24.04)":changelog_1_1_v,
	"Версия 1.2(2025.07.07)":changelog_1_2_v,
	
	}

def setup_theme(theme=None):
	if theme == None:
		theme = "dark"
		if os.path.exists(SETTINGS_FILE):
			try:
				with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
					_settings = json.load(file)
					theme = _settings["theme"]
			except:
				pass
	try:
		qdarktheme.setup_theme(theme)
	except ValueError:
		qdarktheme.setup_theme("dark")
		try:
			with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
				_settings = json.load(file)
			_settings["theme"] = "dark"
			with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
				json.dump(_settings, f, indent=4, ensure_ascii=False)
		except:
			pass




class Updater(QThread):
	critical = pyqtSignal(str,str)
	information = pyqtSignal(str,str)
	progress = pyqtSignal(int)
	started_downloading = pyqtSignal()
	done = pyqtSignal(str) 
	cancel = False
	def stop(self):
		self.cancel = True

	def __init__(self, has_req:bool,download_url):
		super().__init__()
		self.has_req = has_req
		self.download_url = download_url
	def run(self):
		def update_program():
			try:
				current_exe = sys.executable
				new_exe = current_exe + ".new"
				self.started_downloading.emit()
				try:
					response = requests.get(self.download_url, stream=True)
					total = int(response.headers.get('content-length', 0))
					downloaded = 0

					with open(new_exe, 'wb') as f:
						for chunk in response.iter_content(chunk_size=8192):
							if chunk:
								f.write(chunk)
								downloaded += len(chunk)
								percent = int(downloaded * 100 / total)
								self.progress.emit(percent)
								if self.cancel:
									print("Обновление отменено пользователем.")
									return
					exe_name = os.path.basename(current_exe)
					new_name = os.path.basename(new_exe)
					bat_path = os.path.join(os.path.dirname(current_exe), "update.bat")

					with open(bat_path, "w", encoding="utf-8-sig") as bat:
						bat.write(f"""@echo off
chcp 65001 >nul
echo Ожидание завершения программы...
ping 127.0.0.1 -n 5 >nul
:loop
tasklist | find /i "{exe_name}" >nul
if not errorlevel 1 (
ping 127.0.0.1 -n 2 >nul
goto loop
)
del "{exe_name}" >nul
rename "{new_name}" "{exe_name}"
start "" "{exe_name}"
del "%~f0"
""")
					self.progress.emit(100)
					self.done.emit(bat_path) 
				except Exception as e:
					self.critical.emit(self,"Внимание",f"Ошибка при скачивании обновления {e}")
			except Exception as e:
				self.critical.emit("Внимание",f"Ошибка при проверке обновления {e}")
		update_program()




class Worker(QThread):
	progress_signal = pyqtSignal(int)
	log_signal = pyqtSignal(str)
	color = pyqtSignal(QColor)
	finished = pyqtSignal()


	def __init__(self, x_range, y_range, z_range, blocks_list, path, bedrock_floor_checked,sum_,use_custom_list,diapason, game_version,bedrock_coords):
		super().__init__()
		self.x_range = x_range
		self.y_range = y_range
		self.z_range = z_range
		self.blocks_list = blocks_list
		self.path = path
		self.bedrock_floor_checked = bedrock_floor_checked
		self.sum_ = sum_
		self.use_custom_list = use_custom_list
		self.diapason = diapason
		self.game_version = ("java", game_version)
		self.bedrock_coords = bedrock_coords
	#self.log_signal.emit("")
	#self.progress_signal.emit(i)
	def run(self):
		block_usage_count = {}
		blocks_count = 0
		err_text = "Ошибки:"
		logfile_nametime = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
		start_time = datetime.now()
		try:
			level = amulet.load_level(self.path)
			try:
				with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
					_settings = json.load(file)
				if self.path in _settings["recent_worlds"]:
					_settings["recent_worlds"].remove(self.path)
				_settings["recent_worlds"].insert(0, self.path)
				_settings["recent_worlds"] = _settings["recent_worlds"][:5]    
				with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
					json.dump(_settings, f, indent=4, ensure_ascii=False)
			except Exception as e:
				print(e)
			if self.bedrock_floor_checked:
				for x in self.x_range:
					for z in self.z_range:
						self.msleep(25)
						block = Block(base_name="bedrock", namespace="minecraft")
						level.set_version_block(x, self.bedrock_coords, z,"minecraft:overworld",self.game_version,block)
						blocks_count +=1
						block_usage_count["bedrock"] = block_usage_count.get("bedrock", 0) + 1
						progress = int((blocks_count / self.sum_) * 100)
						self.progress_signal.emit(progress)
						setblock_time = datetime.now()
						setblock_time = setblock_time.strftime('%d.%m.%Y %H:%M:%S.') + f'{setblock_time.microsecond // 1000:03}'
						self.log_signal.emit(f"[{setblock_time}] {x} -64 {z}: minecraft:bedrock")
			for y in self.y_range:
				for x in self.x_range:
					for z in self.z_range:
						self.msleep(25)
						rnd_block = random.choice(self.blocks_list)
						block = Block(base_name=rnd_block, namespace="minecraft")
						level.set_version_block(x, y, z,"minecraft:overworld",self.game_version,block)
						blocks_count +=1
						block_usage_count[rnd_block] = block_usage_count.get(rnd_block, 0) + 1
						progress = int((blocks_count / self.sum_) * 100)
						self.progress_signal.emit(progress)
						self.log_signal.emit(f"[{datetime.now().strftime('%d.%m.%Y %H:%M:%S.') + f'{datetime.now().microsecond // 1000:03}'}] {x} {y} {z}: minecraft:{rnd_block}")
			self.log_signal.emit(f"[+] Сохранение")
			level.save()
			level.close()
			block_usage_count = dict(sorted(block_usage_count.items(), key=lambda item: item[1], reverse=True))
			self.log_signal.emit(f"[✓] Мир сохранен ({datetime.now().strftime('%d.%m.%Y %H:%M:%S.') + f'{datetime.now().microsecond // 1000:03}'})")
			self.log_signal.emit(f"Использованые блоки")
			for key, value in block_usage_count.items():
				self.color.emit(QColor(0, 0, 0))
				self.log_signal.emit(f"{key}: ")
				self.color.emit(QColor(0, 0, 255))
				self.log_signal.emit(f"{value}")
			self.color.emit(QColor(0, 0, 0))
		except amulet.api.errors.LoaderNoneMatched:
			self.log_signal.emit(f"[×] Это не папка с миром")
			err_text += f"\n[{datetime.now().strftime('%d.%m.%Y %H:%M:%S.') + f'{datetime.now().microsecond // 1000:03}'}] Папка не с миром"
			blocks_count = 0
		except Exception as e:
			self.log_signal.emit(f"[×] Ошибка: {e}")
			err_text += f"\n[{datetime.now().strftime('%d.%m.%Y %H:%M:%S.') + f'{datetime.now().microsecond // 1000:03}'}] {e}"
		end_time = datetime.now()
		time_difference = end_time - start_time
		hours = time_difference.seconds // 3600
		minutes = (time_difference.seconds % 3600) // 60
		seconds = time_difference.seconds % 60
		if self.use_custom_list:
			ext = f"\nСписок блоков: {', '.join(self.blocks_list)}"
		else:
			ext = ""
		if err_text == "Ошибки:":
			err_text = ""
		block_usage = "\n".join(f"{key}: {value}" for key, value in block_usage_count.items())
		try:
			with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
				_settings = json.load(file)
		except:
			if_create_log_file = True
		if_create_log_file = _settings["logging_enabled"]
		if if_create_log_file == True:
			log_file_text = f"Генерация начата: {logfile_nametime}\nГенерация завершена: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\nПрошло времени: {hours} ч {minutes} минут {seconds} секунд\nКоличество сгенерированных блоков: {self.sum_}\nИспользование кастомного списка блоков: {self.use_custom_list}{ext}\nБедрок на -64 координате: {self.bedrock_floor_checked}\nДиапазон координат: {self.diapason}\nИспользованные блоки:\n{block_usage}{err_text}".replace("True","да").replace("False","нет")
			try:
				file_name = f"generation_log_{logfile_nametime}.log".replace(":","_")
				with open(file_name, "w", encoding="utf-8") as file:
					file.write(log_file_text)
				self.log_signal.emit(f"[✓] Лог-файл сохранен в {file_name}")
			except:
				pass
		self.finished.emit()

class ChangelogWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		setup_theme()
		stylesheet = qdarktheme.setup_theme(corner_shape="sharp")
		central_widget = QWidget(self)
		self.setCentralWidget(central_widget)
		self.setWindowTitle("Список изменений")
		self.setFixedSize(800,800)
		container = QWidget()
		layout = QVBoxLayout(container)
		layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
		for version, log in changelogs.items():
			title_label = QLabel(f"<b><span style='font-size:14pt'>{version}</span></b>")
			layout.addWidget(title_label)

			formatted_log = log.replace('\n', '<br>')
			log_label = QLabel(f"<span style='font-size:10pt'>{formatted_log}</span>")
			log_label.setWordWrap(True)
			log_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # <— вот эта строка важна
			log_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # если хочешь, чтобы можно было копировать текст
			layout.addWidget(log_label)
		scroll_area = QScrollArea(self)
		scroll_area.setWidget(container)
		scroll_area.setWidgetResizable(True)

		# Устанавливаем layout для центрального виджета
		main_layout = QVBoxLayout(central_widget)
		main_layout.addWidget(scroll_area)

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		auto_update = True
		if os.path.exists(SETTINGS_FILE):
			try:
				with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
					_settings = json.load(file)
					auto_update = _settings["auto_update"]
			except ValueError:
				try:
					with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
						_settings = json.load(file)
					_settings["theme"] = "dark"
					with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
						json.dump(_settings, f, indent=4, ensure_ascii=False)
				except:
					pass
			except:
				pass
		if auto_update == True:
			self.update(True)
		screen = QGuiApplication.primaryScreen()
		size = screen.size()
		width, height = size.width(), size.height()
		if width >= 1360 or height >= 750:
			self.setFixedSize(1360,750)
		else:
			self.setMinimumSize(1024, 768)
			self.showMinimized()
			
		setup_theme()
		stylesheet = qdarktheme.setup_theme(corner_shape="sharp")

		central_widget = QWidget(self)
		self.setCentralWidget(central_widget)
		self.setWindowTitle("Генератор Minecraft миров со случайными блоками")
		self.is_running = False
		container = QWidget()
		
		
		self.path_input = QLineEdit(self)
		self.path_input.setPlaceholderText("Путь к вашему майнкрафт миру")
		self.path_input.setFixedWidth(600)
		self.path_button = QPushButton("Выбрать папку с миром",self)
		self.path_button.setMaximumWidth(self.path_button.sizeHint().width())
		self.path_button.clicked.connect(self.select_path)
		self.version = QComboBox()
		self.versions = ["1.21.6-1.21.7","1.21.5","1.21.4","1.21-1.21.3","1.20.x","1.19.x","1.18.x","1.17.x","1.16.x","1.15.x","1.14.x","1.13.1-1.13.2","1.13","1.12.2"]
		self.version.addItems(self.versions)
		self.version.currentTextChanged.connect(self.on_version_changed)
		self.if_create_log_file = QCheckBox("создавать лог файл")
		self.if_create_log_file.clicked.connect(self.logging_checkbox_enabled_changed)

		self.bedrock_floor = QCheckBox("Сгенерировать пол из бедрока на -64 высоте")
		self.bedrock_floor.stateChanged.connect(self.bedrock_floor_changed)
		self.from_x = QSpinBox()
		self.from_x.setRange(-29999500,29999500)
		self.from_y = QSpinBox()
		self.from_y.setRange(-64,319)
		self.from_z = QSpinBox()
		self.from_z.setRange(-29999500,29999500)
		self.to_x = QSpinBox()
		self.to_x.setRange(-29999500,29999500)
		self.to_y = QSpinBox()
		self.to_y.setRange(-64,319)
		self.to_z = QSpinBox()
		self.to_z.setRange(-29999500,29999500)
		self.custom_block_select = QCheckBox("Выбрать определенные блоки со списка")
		self.custom_block_select.stateChanged.connect(self.select_custom_block_changed)
		self.selected_blocks_list = QListWidget()
		self.selected_blocks_list.setDisabled(True)
		self.selected_blocks_list.setFixedSize(300,500)
		self.select_block_list = QComboBox()
		self.select_block_list.setDisabled(True)
		self.add_block_to_list = QPushButton("Добавить")
		self.add_block_to_list.setDisabled(True)
		self.add_block_to_list.clicked.connect(self.addblocktolist_action)
		self.remove_block_from_list = QPushButton("Удалить")
		self.remove_block_from_list.setDisabled(True)
		self.remove_block_from_list.clicked.connect(self.remblockfromlist_action)
		self.log_info = QTextEdit()
		self.log_info.setPlaceholderText("Логи")
		self.log_info.setReadOnly(True)
		self.progressbar = QProgressBar()
		self.start_button = QPushButton("Начать генерацию")
		self.start_button.clicked.connect(self.main_function)
		self.github_button = QPushButton("GitHub репозиторий проекта")
		self.github_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/GidesPC/MinecraftRandomBlockGenerator")))
		self.changelog_button = QPushButton("Список изменений")
		self.changelog_button.clicked.connect(self.open_changelog_window)
		sel_version = f"{self.version.currentText()}.json"
		if getattr(sys, 'frozen', False):
			json_path = os.path.join(sys._MEIPASS, sel_version)
		else:
			json_path = sel_version
		with open(json_path,"r", encoding='utf-8') as file:
			data = json.load(file)
		self.select_block_list.addItems(list(data["minecraft"].values()))

		self.dark_theme = QRadioButton("Тёмная тема")
		self.light_theme = QRadioButton("Светлая тема")
		theme_values = {
		"dark":self.dark_theme,
		"light":self.light_theme,
		}
		self.dark_theme.clicked.connect(partial(self.change_theme, "dark"))
		self.light_theme.clicked.connect(partial(self.change_theme, "light"))
		theme = "dark"
		if os.path.exists(SETTINGS_FILE):
			try:
				with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
					_settings = json.load(file)
					theme = _settings["theme"]
			except:
				pass
		theme_values[theme].setChecked(True)
		self.auto_updates_ = QCheckBox("Автообновление")
		self.auto_updates_.clicked.connect(self.autoupdates_changed)
		auto_update = True
		if os.path.exists(SETTINGS_FILE):
			try:
				with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
					_settings = json.load(file)
					auto_update = _settings["auto_update"]
			except:
				pass
		self.auto_updates_.setChecked(auto_update)
		self.update_button = QPushButton("Проверить обновления")
		self.update_button.clicked.connect(self.update)
		
		layout = QVBoxLayout(container)
		layout_2 = QHBoxLayout()
		layout_2.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
		layout_3 = QHBoxLayout()
		layout_3.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
		layout_4 = QHBoxLayout()
		layout_4.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
		layout_5 = QHBoxLayout()
		layout_5.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
		layout_6 = QHBoxLayout()
		layout_6.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
		layout_7 = QHBoxLayout()
		layout_7.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
		settings_layout = QHBoxLayout()
		settings_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

		layout.addLayout(layout_2)
		layout.addLayout(layout_3)
		layout.addLayout(settings_layout)
		layout.addLayout(layout_5)
		layout.addLayout(layout_4)
		layout.addLayout(layout_6)
		layout.addLayout(layout_7)
		self.load_settings()

		layout_2.addWidget(self.path_input)
		layout_2.addWidget(self.path_button)
		version_label = QLabel("Версия: ")
		version_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
		layout_2.addWidget(version_label)
		layout_2.addWidget(self.version)
		settings_layout.addWidget(self.if_create_log_file)
		settings_layout.addWidget(self.dark_theme)
		settings_layout.addWidget(self.light_theme)
		settings_layout.addWidget(self.auto_updates_)
		settings_layout.addWidget(self.update_button)
		
		layout_3.addWidget(QLabel("с"))
		layout_3.addWidget(QLabel("x:"))
		layout_3.addWidget(self.from_x)
		layout_3.addWidget(QLabel("y:"))
		layout_3.addWidget(self.from_y)
		layout_3.addWidget(QLabel("z:"))
		layout_3.addWidget(self.from_z)
		layout_3.addWidget(QLabel("по"))
		layout_3.addWidget(QLabel("x:"))
		layout_3.addWidget(self.to_x)
		layout_3.addWidget(QLabel("y:"))
		layout_3.addWidget(self.to_y)
		layout_3.addWidget(QLabel("z:"))
		layout_3.addWidget(self.to_z)
		layout_3.addWidget(self.bedrock_floor)
		layout_3.addWidget(self.custom_block_select)
		layout_3.addWidget(self.start_button)
		layout_4.addWidget(self.selected_blocks_list)
		layout_4_1 = QVBoxLayout()
		layout_4_1.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
		layout_4_1.addWidget(self.select_block_list)
		layout_4_1.addWidget(self.add_block_to_list)
		layout_4_1.addWidget(self.remove_block_from_list)
		layout_4.addLayout(layout_4_1)
		layout_4.addWidget(self.log_info)
		layout_5.addWidget(self.progressbar)
		layout_6.addWidget(QLabel('<span style="color: red;">'
						  'Не используйте свои основные миры, в случае неудачи вы можете их частично испортить, или вовсе сломать. '
						  'Рекомендуется использовать плоские миры.</span>'))
		layout_7.addWidget(QLabel("Версия 1.2, разработано GidesPC"))
		layout_7.addWidget(self.changelog_button)
		layout_6.addWidget(self.github_button)

		container.setLayout(layout)

		scroll_area = QScrollArea(self)
		scroll_area.setWidget(container)
		scroll_area.setWidgetResizable(False) 

		container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

		main_layout = QVBoxLayout(central_widget)
		main_layout.addWidget(scroll_area)
		
		menu_bar = self.menuBar()
		self.file_menu = menu_bar.addMenu("Файл")

		self.contextmenu_open = QAction("Выбрать папку с миром",self)
		self.file_menu.addAction(self.contextmenu_open)
		self.contextmenu_open.triggered.connect(self.select_path)

		self.recent_worlds_menu = QMenu("Открыть последние миры", self)
		self.file_menu.addMenu(self.recent_worlds_menu)
		
		lang_menu = menu_bar.addMenu("Язык (Language)")
		ru = QAction("Русский",self)
		en = QAction("English",self)
		en.triggered.connect(self.en_translated)
		lang_menu.addAction(ru)
		lang_menu.addAction(en)
		self.update_recent_worlds_menu()
			
	def update(self ,has_req:False):
		if not getattr(sys, 'frozen', False):
			print("Запущено не из .exe, обновление не требуется")
			return
		try:
			response = requests.get(GITHUB_RELEASES, timeout=5)
			releases = response.json()
			latest = releases[0]
			download_url = latest["assets"][0]["browser_download_url"]
			new_version = latest["name"]
			if current_version != new_version:
				if has_req:
					msg = QMessageBox.information(self,"Обновление",f"Доступно новая версия ({new_version}), обновиться?", buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
					msg = msg == QMessageBox.StandardButton.Yes
				else:
					msg = True
				if msg == True:
					self.updater = Updater(True,download_url)
					self.updater.progress.connect(self.set_progress_value)
					self.updater.started_downloading.connect(self.show_progress_dialog)
					self.updater.critical.connect(self.critical)
					self.updater.information.connect(self.critical)
					self.updater.done.connect(self.on_update_done)
					self.updater.start()
			else:
				if not has_req:
					QMessageBox.information(self,"Обновление","Обновления не найдены")

		except Exception as e:
			if not has_req:
				QMessageBox.critical(self,"Внимание",f"Ошибка при проверке обновлений {e}")

	def autoupdates_changed(self):
		try:
			with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
				_settings = json.load(file)
			_settings["auto_update"] = self.auto_updates_.isChecked()
			with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
				json.dump(_settings, f, indent=4, ensure_ascii=False)
		except Exception as e:
			QMessageBox.critical(self,"Внимание",f"Ошибка при изменении настроек {e}")

	def change_theme(self,theme):
		try:
			with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
				_settings = json.load(file)
			_settings["theme"] = theme
			with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
				json.dump(_settings, f, indent=4, ensure_ascii=False)
		except Exception as e:
			QMessageBox.critical(self,"Внимание",f"Ошибка при изменении настроек {e}")
		setup_theme(theme)

	def open_changelog_window(self):
		self.changelog_window = ChangelogWindow()
		self.changelog_window.show()

	def load_recent_worlds(self):
		try:
			with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
				_settings = json.load(file)
			return _settings["recent_worlds"]
		except Exception as e:
			print(e)
			return []
	def update_recent_worlds_menu(self):
		self.recent_worlds_menu.clear()
		recent_worlds = self.load_recent_worlds()
		if not recent_worlds:
			action = QAction("Нет сохранённых миров", self)
			action.setEnabled(False)
			self.recent_worlds_menu.addAction(action)
		else:
			for path in recent_worlds:
				action = QAction(path, self)
				action.triggered.connect(lambda checked, p=path: self.open_world(p))
				self.recent_worlds_menu.addAction(action)
	def logging_checkbox_enabled_changed(self):
		loading = self.load_settings(self.if_create_log_file.isChecked())
		if not loading:
			self.if_create_log_file.setChecked(True)
			print("чо")

	def load_settings(self,logging_enabled:bool=None):
		if logging_enabled == None:
			if os.path.exists(SETTINGS_FILE):
				with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
					_settings = json.load(file)
				self.if_create_log_file.setChecked(_settings["logging_enabled"])
			else:
				default_settings = {
				"logging_enabled": True,
				"theme":"dark",
				"auto_update":True,
				"recent_worlds":[]
				}
				with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
					json.dump(default_settings, f, indent=4, ensure_ascii=False)
				self.if_create_log_file.setChecked(True)
		elif logging_enabled != None:
			try:
				with open(SETTINGS_FILE,"r", encoding='utf-8') as file:
					_settings = json.load(file)
				_settings["logging_enabled"] = logging_enabled
				with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
					json.dump(_settings, f, indent=4, ensure_ascii=False)
				return True
			except Exception as e:
				QMessageBox.critical(self,"Внимание",f"Ошибка при изменении настроек {e}")
				return False
	def en_translated(self):
		QMessageBox.information(self,"!!!","Translation soon...")
	def select_path(self):
		folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку с майнкрафт миром")
		self.path_input.setText(folder_path)
	def open_world(self,path):
		self.path_input.setText(path)
	def on_version_changed(self):
		sel_version = f"{self.version.currentText()}.json"
		if getattr(sys, 'frozen', False):
			json_path = os.path.join(sys._MEIPASS, sel_version)
		else:
			json_path = sel_version
		with open(json_path,"r", encoding='utf-8') as file:
			data = json.load(file)
		self.select_block_list.clear()
		self.select_block_list.addItems(list(data["minecraft"].values()))
		data = data["minecraft"]
		valid_blocks = set(data.values())
		for i in reversed(range(self.selected_blocks_list.count())):
			item_text = self.selected_blocks_list.item(i).text()
			if item_text not in valid_blocks:
				self.selected_blocks_list.takeItem(i)
		if self.version.currentIndex() >= len(self.versions) - 7:
			self.bedrock_floor.setText("Сгенерировать пол из бедрока на 0 высоте")
			self.from_y.setRange(0,255)
			self.to_y.setRange(0,255)
		else:
			self.bedrock_floor.setText("Сгенерировать пол из бедрока на -64 высоте")
			self.from_y.setRange(-64,319)
			self.to_y.setRange(0,255)

	def critical(self, title, text):
		QMessageBox.critical(self,title,text)
	def information(self, title, text):
		QMessageBox.information(self,title,text)
	def show_progress_dialog(self):
		self.progress_dialog = QProgressDialog("Загрузка обновления...", None, 0, 100, self)
		self.progress_dialog.setWindowModality(Qt.WindowModal)
		self.progress_dialog.canceled.connect(self.cancel_download)
		self.progress_dialog.show()
	def cancel_download(self):
		if hasattr(self, 'updater'):
			self.updater.stop()
			self.progress_dialog.close()
	def set_progress_value(self, value):
		if hasattr(self, "progress_dialog"):
			self.progress_dialog.setValue(value)
			if value >= 100:
				self.progress_dialog.close()
	def on_update_done(self, bat_path):
		self.progress_dialog.close()
		os.startfile(bat_path)
		QApplication.quit()
	def bedrock_floor_changed(self):
		if self.bedrock_floor.isChecked():
			self.from_y.setRange(-63,319)
			self.to_y.setRange(-63,319)
		else:
			self.from_y.setRange(-64,319)
			self.to_y.setRange(-64,319)
	def select_custom_block_changed(self):
		if self.custom_block_select.isChecked():
			disabled = False
		else:
			disabled = True
		self.selected_blocks_list.setDisabled(disabled)
		self.select_block_list.setDisabled(disabled)
		self.add_block_to_list.setDisabled(disabled)
		self.remove_block_from_list.setDisabled(disabled)
	def addblocktolist_action(self):
		items = [item.text() for item in self.selected_blocks_list.findItems("", Qt.MatchFlag.MatchContains)]
		selected_item = self.select_block_list.currentText()
		if selected_item in items:
			QMessageBox.critical(self,"Внимание","Этот элемент уже добавлен")
		else:
			self.selected_blocks_list.addItem(selected_item)
	def remblockfromlist_action(self):
		if self.selected_blocks_list.currentItem():
			row = self.selected_blocks_list.currentRow()
			self.selected_blocks_list.takeItem(row)
		else:
			QMessageBox.critical(self,"Внимание","Элемент не выбран")
	def disable_elements(self,disabled):
		elements = [self.path_input,self.path_button,self.bedrock_floor,self.from_x,self.from_y,self.from_z,self.to_x,self.to_y,self.to_z,self.custom_block_select,self.selected_blocks_list,self.select_block_list,self.add_block_to_list,self.remove_block_from_list,self.start_button]
		for element in elements:
			element.setDisabled(disabled)
		self.file_menu.setEnabled(False)
	def main_function(self):
		sum_ = (abs(self.to_x.value() - self.from_x.value())+1) * \
	   (abs(self.to_y.value() - self.from_y.value())+1) * \
	   (abs(self.to_z.value() - self.from_z.value())+1)
		if self.bedrock_floor.isChecked():
			sum_ += (abs(self.to_x.value() - self.from_x.value()+1)) * \
					(abs(self.to_z.value() - self.from_z.value())+1)
		warning_messages = {
			20000: "Будет сгенерировано {sum_} блоков, генерация может занять продолжительное время, продолжить?",
			20000000: "Предупреждение: будет сгенерировано {sum_} блоков. Это может занять значительное время, хотите продолжить?",
			50000000: "Внимание: вы собираетесь сгенерировать {sum_} блоков! Это может занять много времени и ресурсов. Продолжить?",
			100000000: "Внимание, количество блоков составляет {sum_}. Процесс может занять много времени. Вы уверены, что хотите продолжить?",
			250000000: "Порог {sum_} блоков превышен! Генерация может занять много времени и места. Вы хотите продолжить?",
			500000000: "Предупреждение: {sum_} блоков! Это очень большой объем, процесс может занять несколько часов. Продолжить?",
			1000000000: "Очень большое количество блоков — {sum_}! Это может занять значительное время и ресурсы. Вы уверены?",
			2500000000: "Генерация {sum_} блоков потребует очень много времени и места. Ожидайте длительный процесс. Продолжить?",
			5000000000: "Внимание: сгенерировано {sum_} блоков, что может значительно повлиять на производительность. Продолжить?",
			8000000000: "Максимальный предел достигнут: {sum_} блоков! Это может занять много времени, вы хотите продолжить?",
			10000000000: "Генерация {sum_} блоков. Это может занять очень много места и времени. Продолжить?",
			3840076800384: "Вы пытаетесь сгенерировать {sum_} блоков — это крайне большое количество, что может повлиять на производительность и место на диске. Хотите продолжить?",
			1000000000000: "Вы собираетесь сгенерировать {sum_} блоков — это 1 триллион! Генерация может занять много времени и место на диске. Продолжить?",
			2000000000000: "Предупреждение: сгенерировано {sum_} блоков — это 2 триллиона! Процесс может занять крайне много времени и потребовать огромного объема диска. Хотите продолжить?"
		}
		message = None
		complete = False
		for threshold, msg in sorted(warning_messages.items(), reverse=True):
			if sum_ >= threshold:
				message = msg.format(sum_=sum_)
				break
		if message != None and sum_ <= 3840076800384:
			msg = QMessageBox.warning(self,"Предупреждение",message, buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
			if msg == QMessageBox.StandardButton.Yes:
				complete = True
		if sum_ > 3840076800384:
			QMessageBox.critical(self,"Внимание",f"{sum_} - ЭТО СЛИШКОМ БОЛЬШОЕ ЧИСЛО!! ГЕНЕРАЦИЯ БЛОКОВ, ПРЕВЫШАЮЩИХ 3840076800384 БУДЕТ ОТКЛОНЕНА")
			message = False
		if message == None:
			msg = QMessageBox.information(self,"Предупреждение",f"Будет сгенерировано {sum_} блоков, продолжить?", buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
			if msg == QMessageBox.StandardButton.Yes:
				complete = True
		if complete == True:
			self.progressbar.setValue(0)
			self.log_info.clear()
			self.is_running = True
			self.disable_elements(True)
			sel_version = f"{self.version.currentText()}.json"
			if getattr(sys, 'frozen', False):
				json_path = os.path.join(sys._MEIPASS, sel_version)
			else:
				json_path = sel_version
			with open(json_path,"r", encoding='utf-8') as file:
				data = json.load(file)
			blocks_list = [item.text() for item in self.selected_blocks_list.findItems("", Qt.MatchFlag.MatchContains)]
			if self.custom_block_select.isChecked() == False or blocks_list == []: 
				blocks_list = list(data["minecraft"].values())
			path = self.path_input.text()
			self.log_info.append(f"[+] Будет сгенерировано {sum_} блоков")
			self.log_info.append(f"[✓] Начата генерация")
			start_x = self.from_x.value()
			end_x = self.to_x.value()
			start_y = self.from_y.value()
			end_y = self.to_y.value()
			start_z = self.from_z.value()
			end_z = self.to_z.value()
			if start_x < end_x:
				x_range = range(start_x, end_x + 1)  # По возрастанию
			else:
				x_range = range(start_x, end_x - 1, -1)  # По убыванию
			if start_y < end_y:
				y_range = range(start_y, end_y + 1)
			else:
				y_range = range(start_y, end_y - 1, -1)
			if start_z < end_z:
				z_range = range(start_z, end_z + 1)
			else:
				z_range = range(start_z, end_z - 1, -1)
			diapason = f"с {self.from_x.value()} {self.from_y.value()} {self.from_z.value()} по {self.to_x.value()} {self.to_y.value()} {self.to_z.value()}"
			if self.version.currentIndex() >= len(self.versions) - 6:
				bedrock_coords = 0
			else:
				bedrock_coords = -64
			
			self.worker = Worker(x_range, y_range, z_range, blocks_list, path,self.bedrock_floor.isChecked(),sum_,self.custom_block_select.isChecked(),diapason,game_versions[self.version.currentText()],bedrock_coords)
			self.worker.progress_signal.connect(self.update_progress)
			self.worker.log_signal.connect(self.log)
			self.worker.finished.connect(self.on_worker_finished)
			self.worker.color.connect(self.set_color)
			self.worker.start()



	def on_worker_finished(self):
		self.log_info.append(f"[✓] Генерация завершена")
		self.disable_elements(False)
		self.file_menu.setEnabled(True)
		self.select_custom_block_changed()
		self.is_running = False
		QMessageBox.information(self,"ВАЖНО!","Чтобы не было темных участков в мире, выберите мир, в котором была проведена генерация блоков, нажмите *Настроить->Оптимизировать мир, поставьте галочку на Очистить кэш, затем нажмите Я знаю что делаю*")

	def log(self, message):
		self.log_info.append(message)
	def set_color(self, color):
		self.log_info.setTextColor(color)
	def update_progress(self, value):
		self.progressbar.setValue(value)

	def closeEvent(self, event):
		if self.is_running:
			reply = QMessageBox.warning(self, "Предупреждение","Программа все еще выполняет задачу. Вы уверены, что хотите закрыть? Вы рискуете потерять свой мир",QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
			if reply == QMessageBox.StandardButton.No:
				event.ignore()
			else:
				event.accept()
		else:
			event.accept()
app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())