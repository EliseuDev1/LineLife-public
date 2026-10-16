"""Impressão de relatórios PDF por meio da pilha multiplataforma do Qt."""

from math import floor, isfinite, sqrt
from pathlib import Path

from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter

# A imagem temporária do Qt é raster de 32 bpp: este orçamento limita a
# alocação solicitada a aproximadamente 64 MiB por página, mesmo para PDFs
# com caixas de página muito maiores que formatos de impressão usuais.
MAX_PAGE_RENDER_PIXELS = 16_000_000
MAX_PAGE_RENDER_DIMENSION = 8_192


def print_pdf_document(pdf_path: str, printer: QPrinter) -> None:
    """Renderiza cada página do PDF e a envia ao dispositivo QPrinter selecionado."""
    document = _load_pdf_document(pdf_path)
    page_count = document.pageCount()
    if page_count < 1:
        raise ValueError("O relatório PDF não contém páginas para imprimir.")

    page_indices = _get_page_indices(printer, page_count)
    printer.setFullPage(False)
    page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
    if page_rect.width() <= 0 or page_rect.height() <= 0:
        raise RuntimeError("A impressora selecionada não disponibilizou uma área de página válida.")

    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("Não foi possível iniciar o trabalho na impressora selecionada.")

    try:
        render_dpi = min(max(printer.resolution(), 72), 300)
        for page_position, page_index in enumerate(page_indices):
            if page_position and not printer.newPage():
                raise RuntimeError("A impressora não aceitou a próxima página do relatório.")

            page_image = _render_page(document, page_index, render_dpi)
            if page_image.isNull():
                raise RuntimeError(f"Não foi possível renderizar a página {page_index + 1} do relatório.")

            # Com fullPage=False, a origem do QPainter já é o canto da área
            # imprimível. Somar page_rect.x()/y() deslocaria a imagem duas vezes.
            # O target rect faz a escala sem alocar uma segunda QImage.
            scale = min(
                page_rect.width() / page_image.width(),
                page_rect.height() / page_image.height(),
            )
            target_width = page_image.width() * scale
            target_height = page_image.height() * scale
            target_rect = QRectF(
                (page_rect.width() - target_width) / 2,
                (page_rect.height() - target_height) / 2,
                target_width,
                target_height,
            )
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawImage(target_rect, page_image)
    except Exception:
        printer.abort()
        raise
    finally:
        painter.end()

    if printer.printerState() == QPrinter.PrinterState.Error:
        raise RuntimeError("O sistema operacional reportou falha ao enviar o relatório à fila de impressão.")


def _get_page_indices(printer: QPrinter, page_count: int) -> tuple[int, ...]:
    """Respeita todas as páginas ou o intervalo escolhido no diálogo de impressão."""
    print_range = printer.printRange()
    if print_range == QPrinter.PrintRange.Selection:
        raise ValueError("Impressão de seleção não está disponível para o relatório PDF.")

    if print_range == QPrinter.PrintRange.CurrentPage:
        raise ValueError("Impressão da página atual não está disponível para o relatório PDF.")

    if print_range == QPrinter.PrintRange.PageRange:
        first_page = printer.fromPage()
        last_page = printer.toPage()
        if first_page == 0 and last_page == 0:
            raise ValueError("O intervalo de páginas foi selecionado, mas não foi definido.")
        if first_page < 1 or last_page < 1:
            raise ValueError("O intervalo de páginas selecionado está incompleto.")
        if first_page > page_count or last_page > page_count or first_page > last_page:
            raise ValueError("O intervalo de páginas selecionado não existe no relatório.")

        page_indices = []
        page_ranges = printer.pageRanges().toRangeList()
        if not page_ranges:
            raise ValueError("A impressora não forneceu intervalos de páginas válidos.")
        for selected_range in page_ranges:
            range_start = selected_range.from_
            range_end = selected_range.to
            if range_start < 1 or range_end < 1 or range_start > range_end:
                raise ValueError("Um dos intervalos de páginas selecionados é inválido.")
            if range_start > page_count or range_end > page_count:
                raise ValueError("Um dos intervalos selecionados não existe no relatório.")
            page_indices.extend(range(range_start - 1, range_end))
        page_indices = sorted(set(page_indices))
    elif print_range == QPrinter.PrintRange.AllPages:
        page_indices = list(range(page_count))
    else:
        raise ValueError("O modo de intervalo selecionado não é compatível com o relatório PDF.")

    page_order = printer.pageOrder()
    if page_order == QPrinter.PageOrder.LastPageFirst:
        page_indices.reverse()
    elif page_order != QPrinter.PageOrder.FirstPageFirst:
        raise ValueError("A ordem de páginas da impressora não é compatível com o relatório PDF.")

    return tuple(page_indices)


def _render_page(document: QPdfDocument, page_index: int, render_dpi: int) -> QImage:
    """Solicita o raster da página dentro dos limites de memória definidos."""
    page_size_points = document.pagePointSize(page_index)
    image_size = _calculate_render_size(
        page_size_points.width(),
        page_size_points.height(),
        render_dpi,
    )
    return document.render(page_index, image_size)


def _calculate_render_size(width_points: float, height_points: float, render_dpi: int) -> QSize:
    """Converte pontos em pixels sem exceder dimensão nem área raster permitidas."""
    page_area_points = width_points * height_points
    if (
        not isfinite(width_points)
        or not isfinite(height_points)
        or not isfinite(page_area_points)
        or width_points <= 0
        or height_points <= 0
        or page_area_points <= 0
    ):
        raise ValueError("O PDF contém dimensões de página inválidas para impressão.")

    scale = min(
        render_dpi / 72,
        MAX_PAGE_RENDER_DIMENSION / max(width_points, height_points),
        sqrt(MAX_PAGE_RENDER_PIXELS / page_area_points),
    )
    return QSize(
        max(1, floor(width_points * scale)),
        max(1, floor(height_points * scale)),
    )


def get_pdf_page_count(pdf_path: str) -> int:
    """Retorna a quantidade de páginas de um relatório PDF válido."""
    page_count = _load_pdf_document(pdf_path).pageCount()
    if page_count < 1:
        raise ValueError("O relatório PDF não contém páginas para imprimir.")
    return page_count


def _load_pdf_document(pdf_path: str) -> QPdfDocument:
    document = QPdfDocument()
    load_error = document.load(str(Path(pdf_path)))
    if load_error != QPdfDocument.Error.None_:
        raise ValueError(f"Não foi possível abrir o relatório PDF para impressão: {load_error.name}.")
    return document
