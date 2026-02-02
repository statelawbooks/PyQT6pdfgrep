import sys
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QTableWidget,
    QTableWidgetItem, QLabel, QHBoxLayout, QPushButton, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class PDFGrepThread(QThread):
    result_signal = pyqtSignal(str, str)  # line text, pdf path
    finished_signal = pyqtSignal()

    def __init__(self, folder, term):
        super().__init__()
        self.folder = folder
        self.term = term

    def run(self):
        for root, _, files in os.walk(self.folder):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_path = os.path.join(root, file)
                    try:
                        # pdfgrep with -n gives page/line number
                        result = subprocess.run(
                            ["pdfgrep", "-in", self.term, pdf_path],
                            capture_output=True,
                            text=True,
                        )
                        output = result.stdout.strip()
                        if output:
                            for line in output.splitlines():
                                self.result_signal.emit(line, pdf_path)
                    except Exception as e:
                        self.result_signal.emit(f"Error with {pdf_path}: {e}", pdf_path)
        self.finished_signal.emit()


class PDFSearchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Search Tool")
        self.setGeometry(200, 200, 900, 600)
        self.folder_path = ""

        layout = QVBoxLayout()

        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_button = QPushButton("Select Folder")
        self.folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_button)
        layout.addLayout(folder_layout)

        # Search input (Enter triggers search)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term and press Enter...")
        self.search_input.returnPressed.connect(self.start_search)
        layout.addWidget(self.search_input)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["PDF File", "Page", "Matched Text"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.results_table)

        self.setLayout(layout)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select PDF Folder")
        if folder:
            self.folder_path = folder
            self.folder_label.setText(folder)

    def start_search(self):
        term = self.search_input.text().strip()
        if not self.folder_path:
            self.results_table.setRowCount(0)
            self.results_table.setRowCount(1)
            self.results_table.setItem(0, 2, QTableWidgetItem("Please select a folder first."))
            return
        if not term:
            self.results_table.setRowCount(0)
            self.results_table.setRowCount(1)
            self.results_table.setItem(0, 2, QTableWidgetItem("Please enter a search term."))
            return

        # Clear previous results
        self.results_table.setRowCount(0)

        # Start search thread
        self.thread = PDFGrepThread(self.folder_path, term)
        self.thread.result_signal.connect(self.add_result)
        self.thread.finished_signal.connect(lambda: None)  # no button to re-enable
        self.thread.start()

    def add_result(self, line, pdf_path):
        # Split line into page and text
        if ':' in line:
            parts = line.split(':', 1)
            page_or_line = parts[0]
            text = parts[1].strip()
        else:
            page_or_line = ""
            text = line

        row = self.results_table.rowCount()
        self.results_table.insertRow(row)

        # PDF file as button
        btn = QPushButton(os.path.basename(pdf_path))
        btn.clicked.connect(lambda checked, path=pdf_path, pg=page_or_line: self.open_pdf(path, pg))
        self.results_table.setCellWidget(row, 0, btn)

        self.results_table.setItem(row, 1, QTableWidgetItem(page_or_line))
        self.results_table.setItem(row, 2, QTableWidgetItem(text))

    def open_pdf(self, path, page):
        """Open PDF at given page if supported."""
        if not os.path.exists(path):
            return
        try:
            page = int(page) if page.isdigit() else 1
        except:
            page = 1

        try:
            if sys.platform.startswith('darwin'):
                # macOS Preview does not support CLI page jump
                subprocess.Popen(['open', path])
            elif sys.platform.startswith('linux'):
                # Evince example: evince --page-label=12 file.pdf
                subprocess.Popen(['evince', f'--page-label={page}', path])
            elif sys.platform.startswith('win'):
                # Adobe Reader example: AcroRd32.exe /A "page=12" "file.pdf"
                subprocess.Popen(['AcroRd32.exe', f'/A', f'page={page}', path])
        except Exception as e:
            print(f"Failed to open PDF: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFSearchApp()
    window.show()
    sys.exit(app.exec())
