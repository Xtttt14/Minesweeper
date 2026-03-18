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
        self.setMinimumSize(30, 30) 
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
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        
        self.init_ui()
        self.start_game("Easy")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.mine_label = QLabel("💣 000")
        self.mine_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.mine_label.setStyleSheet("color: #d9534f;") 
        
        self.reset_btn = QPushButton("😊")
        self.reset_btn.setFixedSize(40, 40)
        self.reset_btn.setFont(QFont("Segoe UI", 20))
        self.reset_btn.clicked.connect(lambda: self.start_game(self.current_difficulty))
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 2px solid #ccc;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        self.timer_label = QLabel("⏱️ 000")
        self.timer_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.timer_label.setStyleSheet("color: #5bc0de;") 
        
        header_layout.addWidget(self.mine_label)
        header_layout.addStretch()
        header_layout.addWidget(self.reset_btn)
        header_layout.addStretch()
        header_layout.addWidget(self.timer_label)
        
        self.main_layout.addLayout(header_layout)
        
        # Grid
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(1)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.grid_widget)
        
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
                background-color: #f8f9fa;
            }
        """)

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
        
        self.timer_label.setText("⏱️ 000")
        self.mine_label.setText(f"💣 {self.total_mines}")
        self.reset_btn.setText("😊")
        
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
                
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e9ecef;
                        border: 1px solid #adb5bd;
                        border-radius: 2px;
                    }
                    QPushButton:hover {
                        background-color: #dee2e6;
                    }
                """)
                
                self.grid_layout.addWidget(btn, r, c)
                row_buttons.append(btn)
            self.buttons.append(row_buttons)
            
        self.adjustSize()

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
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #e9ecef;
                    border: 1px solid #adb5bd;
                    border-radius: 2px;
                }
                QPushButton:hover {
                    background-color: #dee2e6;
                }
            """)
        else:
            if self.flags < self.total_mines:
                self.cell_states[r][c]['flagged'] = True
                self.flags += 1
                btn.setText("🚩")
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e9ecef;
                        border: 1px solid #adb5bd;
                        color: #f0ad4e;
                        font-size: 14px;
                    }
                """)
        
        self.mine_label.setText(f"💣 {self.total_mines - self.flags}")

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
        bg_color = "#f8f9fa" 
        
        if val == -1:
            text = "💣"
            bg_color = "#d9534f"
            btn.setStyleSheet(f"background-color: {bg_color}; border: 1px solid #ccc; color: white;")
            btn.setText(text)
            self.game_over_loss()
            return
        elif val == 0:
            text = ""
            btn.setStyleSheet(f"background-color: {bg_color}; border: 1px solid #eee;")
        else:
            text = str(val)
            colors = {
                1: "blue", 2: "green", 3: "red", 4: "darkblue", 
                5: "brown", 6: "cyan", 7: "black", 8: "gray"
            }
            style_color = colors.get(val, "black")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    border: 1px solid #eee;
                    color: {style_color};
                    font-weight: bold;
                }}
            """)
            
        btn.setText(text)
        # Note: We do NOT disable the button, so it can still receive clicks for chording

        if val == 0:
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0: continue
                    self.reveal(r + dr, c + dc)

    def update_timer(self):
        if self.timer_running and not self.game_over:
            elapsed = int(time.time() - self.start_time)
            self.timer_label.setText(f"⏱️ {elapsed:03d}")

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
        self.reset_btn.setText("😵")
        
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == -1 and not self.cell_states[r][c]['revealed']:
                     self.cell_states[r][c]['revealed'] = True
                     btn = self.buttons[r][c]
                     btn.setText("💣")
                     btn.setStyleSheet("background-color: #d9534f; color: white; border: 1px solid #ccc;")
                     
        QMessageBox.information(self, "Game Over", "You hit a mine! 💥")

    def game_over_win(self):
        self.game_over = True
        self.timer.stop()
        self.reset_btn.setText("😎")
        elapsed = int(time.time() - self.start_time)
        self.save_best_time(elapsed)
        QMessageBox.information(self, "Congratulations!", f"You won in {elapsed} seconds! 🎉")

    def save_best_time(self, elapsed):
        filename = "best_times.json"
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
            
        difficulty = self.current_difficulty
        if difficulty not in data or elapsed < data[difficulty]:
            data[difficulty] = elapsed
            with open(filename, 'w') as f:
                json.dump(data, f)
            
    def show_best_times(self):
        dialog = BestTimesDialog(self)
        dialog.exec()

def main():
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = MinesweeperWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
