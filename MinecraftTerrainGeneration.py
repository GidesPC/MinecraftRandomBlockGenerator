from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import amulet
from amulet.api.block import Block
import random
import json
import sys
from datetime import datetime

class Worker(QThread):
    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    color = pyqtSignal(QColor)
    finished = pyqtSignal()


    def __init__(self, x_range, y_range, z_range, blocks_list, path, bedrock_floor_checked,sum_,use_custom_list,diapason):
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
        self.game_version = ("java", (1, 21, 4))
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
            if self.bedrock_floor_checked:
                for x in self.x_range:
                    for z in self.z_range:
                        self.msleep(25)
                        block = Block(base_name="bedrock", namespace="minecraft")
                        level.set_version_block(x, -64, z,"minecraft:overworld",self.game_version,block)
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
            ext = f"\nСписок блоков: {", ".join(self.blocks_list)}"
        else:
            ext = ""
        if err_text == "Ошибки:":
            err_text = ""
        log_file_text = f"Генерация начата: {logfile_nametime}\nГенерация завершена: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\nПрошло времени: {hours} ч {minutes} минут {seconds} секунд\nКоличество сгенерированных блоков: {self.sum_}\nИспользование кастомного списка блоков: {self.use_custom_list}{ext}\nБедрок на -64 координате: {self.bedrock_floor_checked}\nДиапазон координат: {self.diapason}\nИспользованные блоки:\n{"\n".join(f"{key}: {value}" for key, value in block_usage_count.items())}{err_text}".replace("True","да").replace("False","нет")
        try:
            file_name = f"generation_log_{logfile_nametime}.log".replace(":","_")
            with open(file_name, "w", encoding="utf-8") as file:
                file.write(log_file_text)
            self.log_signal.emit(f"[✓] Лог-файл сохранен в {file_name}")
        except:
            pass
        self.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
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
        
        with open("minecraft_blocks.json","r", encoding='utf-8') as file:
            data = json.load(file)
        self.select_block_list.addItems(list(data["minecraft"].values()))
        
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

        layout.addLayout(layout_2)
        layout.addLayout(layout_3)
        layout.addLayout(layout_5)
        layout.addLayout(layout_4)
        layout.addLayout(layout_6)
        layout.addLayout(layout_7)

        layout_2.addWidget(self.path_input)
        layout_2.addWidget(self.path_button)
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
                          'Рекомендуется использовать полностью пустой мир (плоский мир со слоем блока воздуха).</span>'))
        layout_7.addWidget(QLabel("ОБЯЗАТЕЛЬНО ИСПОЛЬЗУЙТЕ ВЕРСИЮ МАЙНКРАФТА 1.21.4!! в будущих версиях добавлю поддержку большего количество версий."))
        layout_7.addWidget(QLabel("Версия 1.0, разработано GidesPC"))
        layout_6.addWidget(self.github_button)

        container.setLayout(layout)

        scroll_area = QScrollArea(self)
        scroll_area.setWidget(container)
        scroll_area.setWidgetResizable(False) 

        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(scroll_area)
        
        menu_bar = self.menuBar()
        lang_menu = menu_bar.addMenu("Язык (Language)")
        ru = QAction("Русский",self)
        en = QAction("English",self)
        en.triggered.connect(self.en_translated)
        lang_menu.addAction(ru)
        lang_menu.addAction(en)
        self.showMaximized()

    def en_translated(self):
        QMessageBox.information(self,"!!!",r"Translation is not implemented yet ¯\_(ツ)_/¯")
    def select_path(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку с майнкрафт миром")
        self.path_input.setText(folder_path)
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
            with open("minecraft_blocks.json","r", encoding='utf-8') as file:
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
            self.worker = Worker(x_range, y_range, z_range, blocks_list, path,self.bedrock_floor.isChecked(),sum_,self.custom_block_select.isChecked(),diapason)
            self.worker.progress_signal.connect(self.update_progress)
            self.worker.log_signal.connect(self.log)
            self.worker.finished.connect(self.on_worker_finished)
            self.worker.color.connect(self.set_color)
            self.worker.start()



    def on_worker_finished(self):
        self.log_info.append(f"[✓] Генерация завершена")
        self.disable_elements(False)
        self.select_custom_block_changed()
        self.is_running = False

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