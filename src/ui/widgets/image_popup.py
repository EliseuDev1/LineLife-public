"""Widget de pop-up flutuante para exibição de imagens explicativas ao passar o mouse."""

import os
from typing import Optional
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def resolve_image_path(image_filename: str) -> str:
    """Busca o caminho absoluto da imagem testando locais conhecidos no projeto."""
    candidates = [
        # Relativo ao pacote de widgets (projeto_linha_vida/imagens)
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "imagens", image_filename)),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "projeto_linha_vida", "imagens", image_filename)),
        # Relativo ao diretório de trabalho atual
        os.path.abspath(os.path.join(os.getcwd(), "imagens", image_filename)),
        os.path.abspath(os.path.join(os.getcwd(), "projeto_linha_vida", "imagens", image_filename)),
        # Caminho direto simples
        os.path.abspath(os.path.join("imagens", image_filename)),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


class ImageHoverPopup(QFrame):
    """Janela flutuante translúcida com sombra e visualização de imagem centralizada."""

    def __init__(self, title: str, image_path: str, max_width: int = 540, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 2px solid #38bdf8;
                border-radius: 8px;
                padding: 6px;
            }
            QLabel#title {
                color: #38bdf8;
                font-weight: bold;
                font-size: 13px;
                padding-bottom: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        lbl_title = QLabel(f"ℹ️ {title}")
        lbl_title.setObjectName("title")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        self.lbl_img = QLabel()
        self.lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Limite máximo de altura para não estourar em monitores verticais ou telas 768p/900p
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else None
        max_h = int(screen_geo.height() * 0.70) if screen_geo else 500

        resolved = resolve_image_path(os.path.basename(image_path))
        if os.path.exists(resolved):
            pix = QPixmap(resolved)
            if not pix.isNull():
                scaled_pix = pix.scaled(
                    max_width,
                    max_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.lbl_img.setPixmap(scaled_pix)
            else:
                self.lbl_img.setText(f"[Imagem corrompida: {os.path.basename(resolved)}]")
                self.lbl_img.setStyleSheet("color: #f87171; font-weight: bold; padding: 20px;")
        else:
            self.lbl_img.setText(f"[Imagem não encontrada: {os.path.basename(image_path)}]")
            self.lbl_img.setStyleSheet("color: #f87171; font-weight: bold; padding: 20px;")

        layout.addWidget(self.lbl_img, alignment=Qt.AlignmentFlag.AlignCenter)
        self.adjustSize()


class ImageHelperButton(QPushButton):
    """Botão com ícone de ajuda que exibe a imagem explicativa com posicionamento inteligente na tela."""

    def __init__(self, title: str, image_filename: str, parent: Optional[QWidget] = None):
        super().__init__("ℹ️", parent)
        self.title = title
        self.image_filename = image_filename
        self.image_path = resolve_image_path(image_filename)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip(f"Passe o mouse para visualizar a ilustração: {title}")
        self.setFixedSize(24, 24)
        self.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #0284c7;
                color: #ffffff;
            }
        """)

        self.popup: Optional[ImageHoverPopup] = None

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.image_path = resolve_image_path(self.image_filename)
        if not self.popup:
            self.popup = ImageHoverPopup(self.title, self.image_path)

        # Garante que as dimensões do pop-up estejam calculadas
        self.popup.adjustSize()
        popup_w = self.popup.sizeHint().width() or self.popup.width()
        popup_h = self.popup.sizeHint().height() or self.popup.height()

        # Obtém os limites visíveis da tela onde o botão está renderizado
        screen = self.screen() or QApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else None

        global_btn_pos = self.mapToGlobal(QPoint(0, 0))

        # 1. Posicionamento Horizontal (X):
        # Tenta posicionar à direita do botão
        target_x = global_btn_pos.x() + self.width() + 12

        # Se ultrapassar a borda direita da tela (ex: tela cheia / full screen), abre à esquerda do botão
        if screen_geo and (target_x + popup_w > screen_geo.right() - 10):
            target_x = global_btn_pos.x() - popup_w - 12

        # Trava para não sair pela borda esquerda da tela
        if screen_geo and target_x < screen_geo.left() + 10:
            target_x = screen_geo.left() + 10

        # 2. Posicionamento Vertical (Y):
        # Alinha o centro do popup com o centro do botão
        target_y = global_btn_pos.y() - (popup_h // 2) + (self.height() // 2)

        # Trava para não sair pelo topo ou rodapé da tela
        if screen_geo:
            if target_y < screen_geo.top() + 10:
                target_y = screen_geo.top() + 10
            elif target_y + popup_h > screen_geo.bottom() - 10:
                target_y = screen_geo.bottom() - popup_h - 10

        self.popup.move(QPoint(target_x, target_y))
        self.popup.show()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        if self.popup:
            self.popup.hide()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        if self.popup:
            self.popup.hide()
