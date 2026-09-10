from PySide6.QtWidgets import QApplication
import sys

# Import the UI
from src.ui.test_generator_ui import TestGeneratorUI


def main():
    app = QApplication(sys.argv)

    window = TestGeneratorUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
