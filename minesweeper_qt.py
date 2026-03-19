import sys
import json
import random
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout,
                             QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
                             QMessageBox, QDialog, QTableWidget,
                             QTableWidgetItem, QHeaderView, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

# Increase recursion depth for large areas of empty cells
sys.setrecursionlimit(2000)

class MinesweeperButton(QPushButton):
    right_clicked = pyqtSignal()
    chord_clicked = pyqtSignal()

    def __init__(self, r, c, parent=None):
        super().__init__(parent)
        self.r = r
        self.c = c
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setMinimumSize(16, 16)
        self.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.is_revealed = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit()
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.is_revealed:
                self.chord_clicked.emit()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)


class DigitalLabel(QLabel):
    def __init__(self, text="000", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(78, 42)
        self.setFont(QFont("Consolas", 26, QFont.Weight.Bold))
        self.setStyleSheet("""
            QLabel {
                background-color: #111111;
                color: #ff2a2a;
                border-top: 2px solid #808080;
                border-left: 2px solid #808080;
                border-right: 2px solid #ffffff;
                border-bottom: 2px solid #ffffff;
                padding: 0px 4px 2px 4px;
            }
        """)

class BestTimesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Best Times 🏆")
        self.setFixedSize(300, 200)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Difficulty", "Time (s)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.layout.addWidget(self.table)
        
        self.load_times()

    def load_times(self):
        filename = "best_times.json"
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
            
        difficulties = ["Easy", "Medium", "Hard"]
        self.table.setRowCount(len(difficulties))
        
        for i, diff in enumerate(difficulties):
            time_val = data.get(diff, "N/A")
            self.table.setItem(i, 0, QTableWidgetItem(diff))
            self.table.setItem(i, 1, QTableWidgetItem(str(time_val)))

class MinesweeperWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minesweeper QT")
        
        self.DIFFICULTY = {
            "Easy": {"rows": 9, "cols": 9, "mines": 10},
            "Medium": {"rows": 16, "cols": 16, "mines": 40},
            "Hard": {"rows": 16, "cols": 30, "mines": 99}
        }
        
        self.current_difficulty = "Easy"
        self.rows = 9
        self.cols = 9
        self.total_mines = 10
        
        self.grid = [] 
        self.buttons = [] 
        self.mines_locations = set()
        self.flags = 0
        self.start_time = None
        self.game_over = False
        self.first_click = True
        self.timer_running = False
        self.auto_resizing = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        
        self.init_ui()
        self.start_game("Easy")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(8)

        # Header
        self.header_panel = QWidget()
        self.header_panel.setObjectName("headerPanel")
        header_layout = QHBoxLayout(self.header_panel)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(10)

        self.mine_label = DigitalLabel("010")

        self.reset_btn = QPushButton(":)")
        self.reset_btn.setFixedSize(40, 40)
        self.reset_btn.setFont(QFont("Consolas", 15, QFont.Weight.Bold))
        self.reset_btn.clicked.connect(lambda: self.start_game(self.current_difficulty))
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #c0c0c0;
                color: #000000;
                border-top: 3px solid #ffffff;
                border-left: 3px solid #ffffff;
                border-right: 3px solid #7b7b7b;
                border-bottom: 3px solid #7b7b7b;
                padding: 0px;
                text-align: center;
            }
            QPushButton:pressed {
                border-top: 3px solid #7b7b7b;
                border-left: 3px solid #7b7b7b;
                border-right: 3px solid #ffffff;
                border-bottom: 3px solid #ffffff;
                padding-left: 2px;
                padding-top: 2px;
            }
        """)

        self.timer_label = DigitalLabel("000")

        header_layout.addWidget(self.mine_label)
        header_layout.addStretch()
        header_layout.addWidget(self.reset_btn)
        header_layout.addStretch()
        header_layout.addWidget(self.timer_label)

        self.main_layout.addWidget(self.header_panel)

        # Grid
        self.board_panel = QWidget()
        self.board_panel.setObjectName("boardPanel")
        self.board_layout = QVBoxLayout(self.board_panel)
        self.board_layout.setContentsMargins(6, 6, 6, 6)
        self.board_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.board_layout.addWidget(self.grid_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.board_panel, 1)
        
        # Menu
        menubar = self.menuBar()
        game_menu = menubar.addMenu("Game")
        
        new_game_menu = game_menu.addMenu("New Game")
        new_game_menu.addAction("Easy", lambda: self.start_game("Easy"))
        new_game_menu.addAction("Medium", lambda: self.start_game("Medium"))
        new_game_menu.addAction("Hard", lambda: self.start_game("Hard"))
        
        game_menu.addSeparator()
        game_menu.addAction("Best Times", self.show_best_times)
        game_menu.addSeparator()
        game_menu.addAction("Exit", self.close)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #c0c0c0;
            }
            QWidget {
                background-color: #c0c0c0;
            }
            QWidget#headerPanel, QWidget#boardPanel {
                border-top: 3px solid #7b7b7b;
                border-left: 3px solid #7b7b7b;
                border-right: 3px solid #ffffff;
                border-bottom: 3px solid #ffffff;
            }
            QMenuBar {
                background-color: #c0c0c0;
            }
            QMenuBar::item:selected, QMenu::item:selected {
                background-color: #0a246a;
                color: white;
            }
            QMenu {
                background-color: #c0c0c0;
            }
        """)
        self.setMinimumSize(280, 360)

    def start_game(self, difficulty):
        self.current_difficulty = difficulty
        settings = self.DIFFICULTY[difficulty]
        self.rows = settings["rows"]
        self.cols = settings["cols"]
        self.total_mines = settings["mines"]
        self.reset_game()

    def reset_game(self):
        self.game_over = False
        self.first_click = True
        self.flags = 0
        self.mines_locations = set()
        self.start_time = None
        self.timer_running = False
        self.timer.stop()
        
        self.timer_label.setText("000")
        self.mine_label.setText(f"{self.total_mines:03d}")
        self.reset_btn.setText(":)")
        
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.cell_states = [[{'revealed': False, 'flagged': False} 
                             for _ in range(self.cols)] for _ in range(self.rows)]
        
        self.create_grid_ui()

    def create_grid_ui(self):
        # Efficiently remove old buttons
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        self.buttons = []
        for r in range(self.rows):
            row_buttons = []
            for c in range(self.cols):
                btn = MinesweeperButton(r, c)
                btn.clicked.connect(lambda _, r=r, c=c: self.on_left_click(r, c))
                btn.right_clicked.connect(lambda r=r, c=c: self.on_right_click(r, c))
                btn.chord_clicked.connect(lambda r=r, c=c: self.attempt_chord(r, c))
                
                btn.setFont(QFont("Arial", 13, QFont.Weight.Bold))
                btn.setStyleSheet(self.get_hidden_cell_style())
                
                self.grid_layout.addWidget(btn, r, c)
                row_buttons.append(btn)
            self.buttons.append(row_buttons)

        for r in range(self.rows):
            self.grid_layout.setRowStretch(r, 1)
        for c in range(self.cols):
            self.grid_layout.setColumnStretch(c, 1)

        self.resize_for_current_difficulty()
        self.update_board_geometry()

    def place_mines(self, first_r, first_c):
        mines_placed = 0
        while mines_placed < self.total_mines:
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)
            
            if (r, c) in self.mines_locations:
                continue
            if abs(r - first_r) <= 1 and abs(c - first_c) <= 1:
                continue
                
            self.mines_locations.add((r, c))
            self.grid[r][c] = -1
            mines_placed += 1
            
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == -1:
                    continue
                count = 0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0: continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols and self.grid[nr][nc] == -1:
                            count += 1
                self.grid[r][c] = count

    def on_left_click(self, r, c):
        if self.game_over or self.cell_states[r][c]['flagged']:
            return

        if self.first_click:
            self.place_mines(r, c)
            self.first_click = False
            self.start_time = time.time()
            self.timer_running = True
            self.timer.start(1000)
            self.update_timer()

        self.reveal(r, c)
        self.check_win()

    def on_right_click(self, r, c):
        if self.game_over or self.cell_states[r][c]['revealed']:
            return
            
        btn = self.buttons[r][c]
        
        if self.cell_states[r][c]['flagged']:
            self.cell_states[r][c]['flagged'] = False
            self.flags -= 1
            btn.setText("")
            btn.setStyleSheet(self.get_hidden_cell_style())
        else:
            if self.flags < self.total_mines:
                self.cell_states[r][c]['flagged'] = True
                self.flags += 1
                btn.setText("P")
                btn.setStyleSheet(self.get_hidden_cell_style("#cc0000"))

        self.mine_label.setText(f"{max(self.total_mines - self.flags, 0):03d}")

    def attempt_chord(self, r, c):
        if not self.cell_states[r][c]['revealed']:
            return
            
        val = self.grid[r][c]
        if val <= 0:
            return

        flags_count = 0
        neighbors = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    neighbors.append((nr, nc))
                    if self.cell_states[nr][nc]['flagged']:
                        flags_count += 1
        
        if flags_count == val:
            for nr, nc in neighbors:
                if not self.cell_states[nr][nc]['flagged'] and not self.cell_states[nr][nc]['revealed']:
                    self.reveal(nr, nc)
                    self.check_win()

    def reveal(self, r, c):
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return
        if self.cell_states[r][c]['revealed'] or self.cell_states[r][c]['flagged']:
            return
            
        self.cell_states[r][c]['revealed'] = True
        val = self.grid[r][c]
        btn = self.buttons[r][c]
        
        btn.is_revealed = True
        
        text = ""
        style_color = "black"

        if val == -1:
            text = "*"
            btn.setStyleSheet(self.get_revealed_cell_style("#000000", "#ff0000"))
            btn.setText(text)
            self.game_over_loss()
            return
        elif val == 0:
            text = ""
            btn.setStyleSheet(self.get_revealed_cell_style())
        else:
            text = str(val)
            colors = {
                1: "#0000ff", 2: "#008000", 3: "#ff0000", 4: "#000080",
                5: "#800000", 6: "#008080", 7: "#000000", 8: "#808080"
            }
            style_color = colors.get(val, "black")
            btn.setStyleSheet(self.get_revealed_cell_style(style_color))
            
        btn.setText(text)
        # Note: We do NOT disable the button, so it can still receive clicks for chording

        if val == 0:
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0: continue
                    self.reveal(r + dr, c + dc)

    def update_timer(self):
        if self.timer_running and not self.game_over:
            elapsed = self.get_elapsed_seconds()
            self.timer_label.setText(f"{min(elapsed, 999):03d}")

    def check_win(self):
        if self.game_over: return
        
        revealed_count = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if self.cell_states[r][c]['revealed']:
                    revealed_count += 1
                    
        if revealed_count == (self.rows * self.cols) - self.total_mines:
            self.game_over_win()

    def game_over_loss(self):
        self.game_over = True
        self.timer.stop()
        self.reset_btn.setText("X(")
        
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == -1 and not self.cell_states[r][c]['revealed']:
                     self.cell_states[r][c]['revealed'] = True
                     btn = self.buttons[r][c]
                     btn.setText("*")
                     btn.setStyleSheet(self.get_revealed_cell_style("#000000"))

        QMessageBox.information(self, "Game Over", "You hit a mine!")

    def game_over_win(self):
        self.game_over = True
        self.timer.stop()
        self.reset_btn.setText("B)")
        elapsed = self.get_elapsed_seconds()
        self.timer_label.setText(f"{min(elapsed, 999):03d}")
        self.save_best_time(elapsed)
        QMessageBox.information(self, "Congratulations!", f"You won in {elapsed} seconds!")

    def save_best_time(self, elapsed):
        filename = "best_times.json"
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        difficulty = self.current_difficulty
        current_best = data.get(difficulty)
        if not isinstance(current_best, int) or current_best <= 0:
            current_best = None

        if current_best is None or elapsed < current_best:
            data[difficulty] = elapsed
            with open(filename, 'w') as f:
                json.dump(data, f)
            
    def show_best_times(self):
        dialog = BestTimesDialog(self)
        dialog.exec()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_board_geometry()

    def resize_for_current_difficulty(self):
        target_cell_sizes = {
            "Easy": 42,
            "Medium": 30,
            "Hard": 24
        }
        cell_size = target_cell_sizes.get(self.current_difficulty, 30)

        board_width = self.cols * cell_size
        board_height = self.rows * cell_size
        self.grid_widget.setMinimumSize(board_width, board_height)
        self.board_panel.setMinimumSize(board_width + 20, board_height + 20)
        self.centralWidget().adjustSize()

        size_hint = self.sizeHint()
        target_width = max(board_width + 52, size_hint.width())
        target_height = max(board_height + 172, size_hint.height())

        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            target_width = min(target_width, int(available.width() * 0.9))
            target_height = min(target_height, int(available.height() * 0.9))

        self.auto_resizing = True
        self.resize(max(target_width, 320), max(target_height, 420))
        self.auto_resizing = False

    def update_board_geometry(self):
        if not self.buttons:
            return

        margins = self.board_layout.contentsMargins()
        board_width = max(0, self.board_panel.width() - margins.left() - margins.right() - 10)
        board_height = max(0, self.board_panel.height() - margins.top() - margins.bottom() - 10)
        if board_width <= 0 or board_height <= 0:
            return

        cell_size = max(16, min(board_width // self.cols, board_height // self.rows))
        grid_width = cell_size * self.cols
        grid_height = cell_size * self.rows
        self.grid_widget.setFixedSize(grid_width, grid_height)

        font_size = max(9, min(20, int(cell_size * 0.45)))
        for row in self.buttons:
            for btn in row:
                btn.setMinimumSize(cell_size, cell_size)
                btn.setMaximumSize(cell_size, cell_size)
                btn.setFont(QFont("Arial", font_size, QFont.Weight.Bold))

    def get_elapsed_seconds(self):
        if self.start_time is None:
            return 0
        return max(1, int(time.time() - self.start_time))

    def get_hidden_cell_style(self, text_color="#000000"):
        return f"""
            QPushButton {{
                background-color: #c0c0c0;
                color: {text_color};
                border-top: 3px solid #ffffff;
                border-left: 3px solid #ffffff;
                border-right: 3px solid #7b7b7b;
                border-bottom: 3px solid #7b7b7b;
                padding: 0px;
            }}
            QPushButton:pressed {{
                border-top: 3px solid #7b7b7b;
                border-left: 3px solid #7b7b7b;
                border-right: 3px solid #ffffff;
                border-bottom: 3px solid #ffffff;
            }}
        """

    def get_revealed_cell_style(self, text_color="#000000", bg_color="#c0c0c0"):
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border-top: 1px solid #7b7b7b;
                border-left: 1px solid #7b7b7b;
                border-right: 1px solid #f2f2f2;
                border-bottom: 1px solid #f2f2f2;
                padding: 0px;
                font-weight: bold;
            }}
        """

def main():
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = MinesweeperWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
