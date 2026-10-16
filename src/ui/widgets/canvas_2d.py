"""Widget de visualização gráfica 2D esquemática de postes e vãos de linha de vida."""

from typing import List, Optional
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QWidget
from src.domain.models import SpanGeometry


class Lifeline2DCanvas(QGraphicsView):
    """Canvas gráfico vetorial 2D renderizando esquematicamente os postes e vãos da linha de vida."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumHeight(180)

        self._spans: List[SpanGeometry] = []
        self._critical_span_index: int = 1
        self._dynamic_sag_mm: float = 0.0

    def set_geometry(
        self,
        spans: List[SpanGeometry],
        critical_span_index: int = 1,
        dynamic_sag_mm: float = 0.0,
    ) -> None:
        """Atualiza os vãos e redesenha a linha esquemática."""
        self._spans = spans
        self._critical_span_index = critical_span_index
        self._dynamic_sag_mm = dynamic_sag_mm
        self.redraw()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.redraw()

    def redraw(self) -> None:
        """Renderiza os postes, vãos, cabo de aço e cotas na cena gráfica."""
        self.scene.clear()
        if not self._spans:
            return

        w = self.viewport().width()
        h = self.viewport().height()
        if w < 100 or h < 100:
            return

        self.scene.setSceneRect(0, 0, w, h)

        num_spans = len(self._spans)
        num_posts = num_spans + 1

        # Margens e coordenadas de desenho
        margin_x = 60.0
        draw_width = w - (2 * margin_x)
        ground_y = h - 45.0
        post_height = 80.0
        post_top_y = ground_y - post_height

        total_length = sum(s.span_mm for s in self._spans)
        if total_length <= 0:
            total_length = 6600.0

        # Posição X de cada poste proporcional ao comprimento real
        post_x_positions = [margin_x]
        accum = 0.0
        for span in self._spans:
            accum += span.span_mm
            x = margin_x + (accum / total_length) * draw_width
            post_x_positions.append(x)

        # 1. Desenha Linha de Solo / Estrutura
        pen_ground = QPen(QColor("#334155"), 2, Qt.PenStyle.DashLine)
        self.scene.addLine(margin_x - 30, ground_y, w - margin_x + 30, ground_y, pen_ground)

        font_label = QFont("Segoe UI", 8)
        font_post = QFont("Segoe UI", 9, QFont.Weight.Bold)

        # 2. Desenha o Cabo de Aço
        pen_cable = QPen(QColor("#38bdf8"), 3)
        for i in range(num_spans):
            x1 = post_x_positions[i]
            x2 = post_x_positions[i + 1]
            # Se for o vão crítico com flecha dinâmica calculada, desenha deflexão
            if (i + 1) == self._critical_span_index and self._dynamic_sag_mm > 0:
                mid_x = (x1 + x2) / 2.0
                sag_pixels = min(self._dynamic_sag_mm * 0.05, 35.0)
                mid_y = post_top_y + sag_pixels

                pen_sag = QPen(QColor("#f43f5e"), 2, Qt.PenStyle.DashLine)
                self.scene.addLine(x1, post_top_y, mid_x, mid_y, pen_sag)
                self.scene.addLine(mid_x, mid_y, x2, post_top_y, pen_sag)

                # Tag de flecha dinâmica
                t_f2 = self.scene.addText(f"f₂ = {self._dynamic_sag_mm:.1f} mm", font_label)
                t_f2.setDefaultTextColor(QColor("#f43f5e"))
                t_f2.setPos(mid_x - 35, mid_y + 4)
            else:
                self.scene.addLine(x1, post_top_y, x2, post_top_y, pen_cable)

        # 3. Desenha os Postes
        for idx, x in enumerate(post_x_positions):
            is_end_post = (idx == 0 or idx == num_posts - 1)
            color_post = QColor("#0284c7") if is_end_post else QColor("#f59e0b")
            pen_post = QPen(color_post, 4)

            # Coluna do poste
            self.scene.addLine(x, ground_y, x, post_top_y, pen_post)

            # Base do poste
            self.scene.addLine(x - 8, ground_y, x + 8, ground_y, QPen(color_post, 3))

            # Ponto de ancoragem no topo
            radius = 6.0 if is_end_post else 4.5
            self.scene.addEllipse(
                x - radius, post_top_y - radius, radius * 2, radius * 2,
                QPen(color_post, 2), QBrush(QColor("#ffffff"))
            )

            # Rótulo do poste
            post_name = f"P{idx + 1}"
            if is_end_post:
                post_name += " (Ext)"
            t = self.scene.addText(post_name, font_post)
            t.setDefaultTextColor(color_post)
            t.setPos(x - 16, ground_y + 4)

        # 4. Desenha as Cotas Dimensionais dos Vãos
        pen_dim = QPen(QColor("#94a3b8"), 1)
        for i in range(num_spans):
            x1 = post_x_positions[i]
            x2 = post_x_positions[i + 1]
            dim_y = post_top_y - 22.0

            # Linha da cota com setas
            self.scene.addLine(x1 + 4, dim_y, x2 - 4, dim_y, pen_dim)
            self.scene.addLine(x1 + 4, dim_y - 3, x1 + 4, dim_y + 3, pen_dim)
            self.scene.addLine(x2 - 4, dim_y - 3, x2 - 4, dim_y + 3, pen_dim)

            # Texto da cota
            span_val_m = self._spans[i].span_mm / 1000.0
            span_text = f"Vão {i + 1}: {self._spans[i].span_mm:.0f} mm ({span_val_m:.2f} m)"
            if (i + 1) == self._critical_span_index and num_spans > 1:
                span_text += " ★ CRÍTICO"

            t_span = self.scene.addText(span_text, font_label)
            t_span.setDefaultTextColor(QColor("#38bdf8") if (i + 1) == self._critical_span_index else QColor("#cbd5e1"))
            text_w = t_span.boundingRect().width()
            t_span.setPos(((x1 + x2) / 2.0) - (text_w / 2.0), dim_y - 18.0)
