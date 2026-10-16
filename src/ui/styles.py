"""Estilos visuais modernos em QSS (Qt Style Sheets) para o aplicativo desktop."""

DARK_THEME_QSS = """
QMainWindow {
    background-color: #1e1e24;
}

QWidget {
    color: #e0e0e0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #33333e;
    background-color: #24242c;
    border-radius: 6px;
    padding: 8px;
}

QTabBar::tab {
    background-color: #1a1a20;
    color: #a0a0b0;
    padding: 7px 10px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 12px;
    font-weight: bold;
}

QTabBar::tab:selected {
    background-color: #24242c;
    color: #38bdf8;
    border-bottom: 2px solid #38bdf8;
}

QTabBar::tab:hover {
    color: #ffffff;
    background-color: #2a2a34;
}

QGroupBox {
    border: 1px solid #3b3b48;
    border-radius: 6px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: #38bdf8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    background-color: #24242c;
}

QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #18181e;
    border: 1px solid #3f3f50;
    border-radius: 4px;
    padding: 6px 10px;
    color: #ffffff;
    selection-background-color: #0284c7;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #38bdf8;
}

QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 6px 10px;
    color: #0f172a;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
}

QComboBox:focus {
    border: 1px solid #0284c7;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left: 1px solid #cbd5e1;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    background-color: #f1f5f9;
}

QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #334155;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
    outline: none;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    min-height: 28px;
    padding: 4px 8px;
    color: #0f172a;
    background-color: #ffffff;
}

QComboBox QAbstractItemView::item:selected, QComboBox QAbstractItemView::item:hover {
    background-color: #0284c7;
    color: #ffffff;
}

QTextEdit {
    background-color: #0b0f19;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 10px;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    line-height: 1.5;
}

QPushButton {
    background-color: #0284c7;
    color: #ffffff;
    border: none;
    border-radius: 5px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #0369a1;
}

QPushButton:pressed {
    background-color: #075985;
}

QPushButton#btn_calculate {
    background-color: #10b981;
    font-size: 14px;
    padding: 10px 24px;
}

QPushButton#btn_calculate:hover {
    background-color: #059669;
}

QPushButton#btn_pdf {
    background-color: #8b5cf6;
    font-size: 13px;
    padding: 8px 18px;
}

QPushButton#btn_pdf:hover {
    background-color: #7c3aed;
}

QPushButton#btn_secondary {
    background-color: #374151;
}

QPushButton#btn_secondary:hover {
    background-color: #4b5563;
}

QTableWidget {
    background-color: #18181e;
    border: 1px solid #33333e;
    gridline-color: #2c2c38;
    color: #f1f5f9;
}

QHeaderView::section {
    background-color: #202028;
    color: #94a3b8;
    padding: 6px;
    border: 1px solid #2c2c38;
    font-weight: bold;
}

QStatusBar {
    background-color: #15151a;
    color: #94a3b8;
    border-top: 1px solid #2a2a35;
}

QToolBar {
    background-color: #1a1a20;
    border-bottom: 1px solid #2e2e38;
    spacing: 6px;
    padding: 4px;
}

QToolButton {
    background-color: transparent;
    color: #e2e8f0;
    padding: 6px 10px;
    border-radius: 4px;
    font-weight: 500;
}

QToolButton:hover {
    background-color: #2d2d38;
}

QGraphicsView {
    background-color: #16161b;
    border: 1px solid #33333e;
    border-radius: 6px;
}

QMenuBar {
    background-color: #181820;
    color: #f1f5f9;
    border-bottom: 1px solid #2e2e38;
}

QMenuBar::item {
    background-color: transparent;
    color: #e2e8f0;
    padding: 6px 12px;
}

QMenuBar::item:selected {
    background-color: #2a2a36;
    color: #38bdf8;
    border-radius: 4px;
}

QMenu {
    background-color: #1a1a24;
    color: #f8fafc;
    border: 1px solid #3b3b4d;
    border-radius: 6px;
    padding: 6px;
}

QMenu::item {
    background-color: transparent;
    color: #f8fafc;
    padding: 6px 28px 6px 12px;
    border-radius: 4px;
    font-size: 13px;
}

QMenu::item:selected {
    background-color: #0284c7;
    color: #ffffff;
}

QMenu::item:disabled {
    color: #64748b;
}

QMenu::separator {
    height: 1px;
    background-color: #333344;
    margin: 4px 6px;
}

QToolTip {
    background-color: #0b0f19;
    color: #f8fafc;
    border: 1px solid #38bdf8;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 12px;
}

QScrollBar:vertical {
    border: none;
    background: #141419;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #3b3b4a;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #0284c7;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QDialog, QMessageBox {
    background-color: #1a1a24;
    color: #f8fafc;
}

QMessageBox QLabel {
    color: #f8fafc;
    background-color: transparent;
    font-size: 13px;
    line-height: 1.4;
    padding: 6px;
}

QMessageBox QPushButton {
    background-color: #0284c7;
    color: #ffffff;
    border: none;
    border-radius: 5px;
    padding: 7px 20px;
    font-size: 13px;
    font-weight: bold;
    min-width: 75px;
}

QMessageBox QPushButton:hover {
    background-color: #0369a1;
}

QMessageBox QPushButton:pressed {
    background-color: #075985;
}

QFileDialog {
    background-color: #1a1a24;
    color: #f8fafc;
}

QFileDialog QLabel {
    color: #f8fafc;
}

QWidget#platform_launcher {
    background-color: #111827;
}

QLabel#launcher_title {
    color: #f8fafc;
    font-size: 32px;
    font-weight: bold;
}

QLabel#launcher_subtitle {
    color: #94a3b8;
    font-size: 15px;
}

QLabel#launcher_footer {
    color: #64748b;
    font-size: 12px;
    padding-top: 8px;
}

QFrame#platform_menu_card {
    background-color: #1f2937;
    border: 1px solid #374151;
    border-radius: 12px;
}

QFrame#platform_menu_card[systemActive="true"] {
    border: 2px solid #38bdf8;
    background-color: #202f42;
}

QFrame#platform_menu_card[systemActive="true"] QLabel#platform_menu_title {
    color: #ffffff;
}

QFrame#platform_menu_card[systemActive="true"] QLabel#platform_menu_status {
    color: #7dd3fc;
}

QFrame#platform_menu_card[systemActive="true"] QLabel#platform_menu_description {
    color: #e2e8f0;
}

QFrame#platform_menu_card:disabled {
    background-color: #182230;
    border-color: #2d3748;
}

QLabel#platform_menu_icon {
    color: #38bdf8;
    font-size: 30px;
    font-weight: bold;
    min-height: 34px;
}

QFrame#platform_menu_card:disabled QLabel#platform_menu_icon {
    color: #64748b;
}

QLabel#platform_menu_title {
    color: #f8fafc;
    font-size: 17px;
    font-weight: bold;
}

QLabel#platform_menu_status {
    color: #38bdf8;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}

QFrame#platform_menu_card:disabled QLabel#platform_menu_status {
    color: #64748b;
}

QLabel#platform_menu_description {
    color: #cbd5e1;
    font-size: 12px;
    line-height: 1.3;
}

QFrame#platform_menu_card:disabled QLabel#platform_menu_title,
QFrame#platform_menu_card:disabled QLabel#platform_menu_description {
    color: #64748b;
}

QPushButton#platform_menu_action {
    background-color: #0284c7;
    border-radius: 6px;
    padding: 9px 16px;
}

QPushButton#platform_menu_action:hover {
    background-color: #0369a1;
}

QPushButton#platform_menu_action:disabled {
    background-color: #334155;
    color: #64748b;
}

/* Regras ativas após os estados genéricos para preservar o contraste do card disponível. */
QFrame#platform_menu_card[systemActive="true"] QLabel#platform_menu_icon {
    color: #7dd3fc;
}

QFrame#platform_menu_card[systemActive="true"] QLabel#platform_menu_title {
    color: #ffffff;
}

QFrame#platform_menu_card[systemActive="true"] QLabel#platform_menu_status {
    color: #7dd3fc;
}

QFrame#platform_menu_card[systemActive="true"] QLabel#platform_menu_description {
    color: #e2e8f0;
}

QPushButton#btn_save {
    background-color: #334155;
    border: 1px solid #64748b;
}

QPushButton#btn_save:hover {
    background-color: #475569;
}

QWidget#stepper {
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 4px;
}

QPushButton#stepper_button {
    background-color: #1e293b;
    border: 1px solid #475569;
    color: #cbd5e1;
    min-height: 34px;
    padding: 7px 10px;
}

QPushButton#stepper_button:hover,
QPushButton#stepper_button:focus {
    border: 2px solid #7dd3fc;
    color: #ffffff;
}

QPushButton#stepper_button[current="true"] {
    background-color: #075985;
    border: 2px solid #7dd3fc;
    color: #ffffff;
}

QGroupBox#verdict_panel {
    border: 2px solid #38bdf8;
    background-color: #172554;
    padding: 12px;
}

QLabel#verdict_label {
    color: #f8fafc;
    font-size: 20px;
    font-weight: 700;
    padding: 8px;
}

QLabel#verdict_label[state="approved"] { color: #6ee7b7; }
QLabel#verdict_label[state="rejected"] { color: #fca5a5; }
QLabel#verdict_label[state="changed"] { color: #fde68a; }

QGroupBox:focus {
    border: 2px solid #7dd3fc;
}

"""
