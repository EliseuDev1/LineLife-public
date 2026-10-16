"""Janela Principal (MainWindow) do aplicativo desktop de Linhas de Vida."""

import os
from typing import List, Optional
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.application.project_service import ProjectService
from src.catalogs.cable_catalog import CableCatalog
from src.catalogs.material_rules import BOMGenerator, BillOfMaterials
from src.core import units
from src.core.license_manager import LicenseManager
from src.core.resource_utils import get_resource_path
from src.domain.installation_types import InstallationBase
from src.domain.models import (
    CableProperties,
    FallClearanceInput,
    LoadRuleType,
    MultiSpanResult,
    SpanGeometry,
    UserLoadConfig,
)
from src.domain.project import Project, ProjectStatus
from src.reports.pdf_generator import CalculationReportGenerator
from src.reports.pdf_printing import get_pdf_page_count, print_pdf_document
from src.ui.styles import DARK_THEME_QSS
from src.ui.widgets.canvas_2d import Lifeline2DCanvas
from src.ui.widgets.image_popup import ImageHelperButton
from src.ui.widgets.installation_forms import InstallationContainerWidget


class _PlatformMenuCard(QFrame):
    """Card reutilizável do launcher, ativo somente quando autorizado."""

    activated = Signal()

    def __init__(
        self,
        icon: str,
        title: str,
        status: str,
        description: str,
        button_text: str,
        enabled: bool,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("platform_menu_card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.setProperty("systemActive", enabled)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        self.icon_label = QLabel(icon)
        self.icon_label.setObjectName("platform_menu_icon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("platform_menu_title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.status_label = QLabel(status)
        self.status_label.setObjectName("platform_menu_status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.description_label = QLabel(description)
        self.description_label.setObjectName("platform_menu_description")
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        layout.addStretch()

        self.action_button = QPushButton(button_text)
        self.action_button.setObjectName("platform_menu_action")
        self.action_button.setEnabled(enabled)
        self.action_button.clicked.connect(self.activate)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.action_button)
        button_row.addStretch()
        self.action_button.setFixedWidth(210)
        layout.addLayout(button_row)

        self.setEnabled(enabled)

    def activate(self) -> None:
        """Ativa o bloco somente se ele estiver habilitado."""
        if self.isEnabled():
            self.activated.emit()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.activate()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activate()
            event.accept()
            return
        super().keyPressEvent(event)


class MainWindow(QMainWindow):
    """Janela principal do aplicativo desktop."""

    LINE_LIFE_STAGE_LABELS = ("Identificação", "Geometria", "Cargas/ZLQ", "Cabo", "Resultados")

    def __init__(
        self,
        service: Optional[ProjectService] = None,
        license_manager: Optional[LicenseManager] = None,
    ):
        super().__init__()
        self.setWindowTitle("LineLife — Public Review")
        self.setWindowIcon(QIcon(get_resource_path(os.path.join("assets", "linelife.ico"))))
        self.resize(1180, 800)
        self.setMinimumSize(980, 680)
        self.setStyleSheet(DARK_THEME_QSS)

        self.license_manager = license_manager or LicenseManager()
        self.service = service or ProjectService(license_manager=self.license_manager)
        if getattr(self.service, "license_manager", None) is None:
            self.service.license_manager = self.license_manager
        self.report_generator = CalculationReportGenerator()
        self.current_project: Project = self.service.create_project()
        self.current_file_path: Optional[str] = None
        self._current_bom: Optional[BillOfMaterials] = None
        self._updating_ui = False
        self._setup_menus_and_toolbar()
        self._setup_central_ui()
        self._setup_platform_navigation()
        self._populate_cables_dropdown()
        self.load_project_to_ui(self.current_project)
        self._update_license_ui()

    def _setup_menus_and_toolbar(self) -> None:
        menubar = self.menuBar()

        # Menu Arquivo
        menu_file = menubar.addMenu("&Arquivo")

        act_new = QAction("&Novo Projeto", self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self._on_action_new)
        menu_file.addAction(act_new)

        act_open = QAction("&Abrir Projeto (.lvd)...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._on_action_open)
        menu_file.addAction(act_open)

        menu_file.addSeparator()

        self.act_save = QAction("&Salvar", self)
        self.act_save.setShortcut("Ctrl+S")
        self.act_save.triggered.connect(self._on_action_save)
        menu_file.addAction(self.act_save)

        self.act_save_as = QAction("Salvar &Como...", self)
        self.act_save_as.setShortcut("Ctrl+Shift+S")
        self.act_save_as.triggered.connect(self._on_action_save_as)
        menu_file.addAction(self.act_save_as)

        self.act_clone = QAction("&Duplicar / Clonar Projeto", self)
        self.act_clone.triggered.connect(self._on_action_clone)
        menu_file.addAction(self.act_clone)

        menu_file.addSeparator()

        act_exit = QAction("Sai&r", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # Menu Relatórios
        menu_reports = menubar.addMenu("&Relatórios")
        self.act_pdf = QAction("📄 &Gerar Memória de Cálculo (PDF)...", self)
        self.act_pdf.setShortcut("Ctrl+P")
        self.act_pdf.triggered.connect(self._on_action_generate_pdf)
        menu_reports.addAction(self.act_pdf)

        self.act_bom = QAction("📊 &Exportar Lista de Materiais (Excel)...", self)
        self.act_bom.triggered.connect(self._on_action_export_bom_excel)
        menu_reports.addAction(self.act_bom)

        self.act_print = QAction("🖨️ &Imprimir Relatório Técnico...", self)
        self.act_print.triggered.connect(self._on_action_print)
        menu_reports.addAction(self.act_print)

        # Menu Cálculo
        menu_calc = menubar.addMenu("&Cálculo")
        self.act_calc = QAction("⚡ &Calcular Linha de Vida", self)
        self.act_calc.setShortcut("F5")
        self.act_calc.triggered.connect(self._on_action_calculate)
        menu_calc.addAction(self.act_calc)

        # Menu Ajuda & Licença
        menu_help = menubar.addMenu("&Ajuda")
        act_license = QAction("🔑 &Gerenciar Licença / Ativar Entitlement Preexistente...", self)
        act_license.setVisible(False)
        menu_help.addAction(act_license)

        act_about = QAction("ℹ️ &Sobre a Plataforma Linha de Vida...", self)
        act_about.triggered.connect(self._on_action_about)
        menu_help.addAction(act_about)

        menu_help.addSeparator()
        self.act_support_project = QAction("Apoiar o projeto", self)
        self.act_support_project.setToolTip(
            "Contribuição voluntária. O processamento e os dados ficam no Mercado "
            "Pago; o apoio não libera recursos adicionais, suporte prioritário, "
            "licença ou vantagem comercial no LineLife."
        )
        self.act_support_project.triggered.connect(
            lambda: self._open_external_support(self.SUPPORT_FIXED_URL)
        )
        menu_help.addAction(self.act_support_project)

        self.act_support_monthly = QAction("Apoiar mensalmente — R$ 19,90", self)
        self.act_support_monthly.setToolTip(
            "Contribuição voluntária. O processamento e os dados ficam no Mercado "
            "Pago; o apoio não libera recursos adicionais, suporte prioritário, "
            "licença ou vantagem comercial no LineLife."
        )
        self.act_support_monthly.triggered.connect(
            lambda: self._open_external_support(self.SUPPORT_MONTHLY_URL)
        )
        menu_help.addAction(self.act_support_monthly)

        # Toolbar
        self.toolbar = self.addToolBar("Ações Rápidas")
        self.toolbar.setMovable(False)
        self.toolbar.addAction(act_new)
        self.toolbar.addAction(act_open)
        self.toolbar.addAction(self.act_save)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.act_calc)
        self.toolbar.addAction(self.act_pdf)
        self.toolbar.addAction(self.act_bom)
        self.toolbar.addSeparator()
        self.toolbar.addAction(act_license)

        self.statusBar().showMessage("Pronto para dimensionamento.")

    def _setup_central_ui(self) -> None:
        self.shell_widget = QWidget()
        main_layout = QVBoxLayout(self.shell_widget)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # Header em duas linhas: contexto do projeto e ações principais.
        self.shell_header = QWidget()
        self.shell_header.setObjectName("shell_header")
        header_layout = QVBoxLayout(self.shell_header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        h_header = QHBoxLayout()
        self.btn_back_to_menu = QPushButton("Voltar ao menu")
        self.btn_back_to_menu.setObjectName("btn_back_to_menu")
        self.btn_back_to_menu.clicked.connect(self.show_main_menu)
        h_header.addWidget(self.btn_back_to_menu)

        self.lbl_project_title_display = QLabel("Novo Projeto")
        self.lbl_project_title_display.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8;")
        h_header.addWidget(self.lbl_project_title_display)

        h_header.addStretch()

        self.btn_license_badge = QPushButton("LOCAL REVIEW")
        self.btn_license_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        h_header.addWidget(self.btn_license_badge)

        self.lbl_status_badge = QLabel("RASCUNHO")
        self.lbl_status_badge.setStyleSheet(
            "background-color: #334155; color: #ffffff; padding: 4px 12px; "
            "border-radius: 4px; font-weight: bold; font-size: 12px;"
        )
        h_header.addWidget(self.lbl_status_badge)
        header_layout.addLayout(h_header)

        h_actions = QHBoxLayout()
        h_actions.setSpacing(8)
        self.btn_save = QPushButton("Salvar")
        self.btn_save.setObjectName("btn_save")
        self.btn_save.clicked.connect(self._on_action_save)
        h_actions.addWidget(self.btn_save)

        self.btn_calculate = QPushButton("Calcular")
        self.btn_calculate.setObjectName("btn_calculate")
        self.btn_calculate.clicked.connect(self._on_action_calculate)
        h_actions.addWidget(self.btn_calculate)

        self.btn_generate_pdf = QPushButton("Gerar PDF")
        self.btn_generate_pdf.setObjectName("btn_pdf")
        self.btn_generate_pdf.clicked.connect(self._on_action_generate_pdf)
        h_actions.addWidget(self.btn_generate_pdf)
        h_actions.addStretch()
        header_layout.addLayout(h_actions)

        main_layout.addWidget(self.shell_header)

        # Abas por etapas
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._update_stepper)

        self.stepper_widget = QWidget()
        self.stepper_widget.setObjectName("stepper")
        stepper_layout = QHBoxLayout(self.stepper_widget)
        stepper_layout.setContentsMargins(0, 0, 0, 0)
        stepper_layout.setSpacing(6)
        self.stepper_buttons = []
        stepper_labels = (
            "Identificação/Instalação",
            "Geometria",
            "Cargas/ZLQ",
            "Cabo de Aço",
            "Resultados/Auditoria",
        )
        for index, label in enumerate(stepper_labels):
            button = QPushButton(label)
            button.setObjectName("stepper_button")
            button.setProperty("current", False)
            button.clicked.connect(
                lambda _checked=False, tab_index=index: self.tabs.setCurrentIndex(tab_index)
            )
            self.stepper_buttons.append(button)
            stepper_layout.addWidget(button)
        main_layout.addWidget(self.stepper_widget)
        main_layout.addWidget(self.tabs)

        self._build_tab_identification()
        self._build_tab_geometry()
        self._build_tab_users_load()
        self._build_tab_cable()
        self._build_tab_results()
        self._build_tab_bom()
        self._update_stepper(self.tabs.currentIndex())

    def _setup_platform_navigation(self) -> None:
        """Monta a entrada principal sem duplicar o shell existente."""
        self._platform_stack = QStackedWidget(self)
        self._main_menu_widget = QWidget()
        self._main_menu_widget.setObjectName("platform_launcher")
        menu_layout = QVBoxLayout(self._main_menu_widget)
        menu_layout.setContentsMargins(72, 48, 72, 42)
        menu_layout.setSpacing(12)

        self.launcher_title = QLabel("Escolha um sistema")
        self.launcher_title.setObjectName("launcher_title")
        self.launcher_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.launcher_title)

        self.launcher_subtitle = QLabel("Selecione um sistema para começar")
        self.launcher_subtitle.setObjectName("launcher_subtitle")
        self.launcher_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.launcher_subtitle)

        blocks_layout = QGridLayout()
        blocks_layout.setHorizontalSpacing(18)
        blocks_layout.setVerticalSpacing(18)
        blocks_layout.setContentsMargins(0, 24, 0, 12)
        menu_layout.addLayout(blocks_layout)
        menu_layout.addStretch()

        self.menu_blocks = []
        menu_items = (
            (
                "⌁",
                "Linha de Vida",
                "DISPONÍVEL",
                "Dimensione linhas de vida horizontais com cálculo e documentação.",
                "Abrir sistema",
                True,
            ),
            (
                "◉",
                "Dimensionamento de Bombas",
                "EM BREVE",
                "Dimensione sistemas de bombeamento para seus projetos.",
                "Em desenvolvimento",
                False,
            ),
            (
                "≋",
                "Dimensionamento de Tubulações",
                "EM BREVE",
                "Dimensione redes de tubulações com segurança.",
                "Em desenvolvimento",
                False,
            ),
            (
                "▦",
                "Gestão de Projetos",
                "EM BREVE",
                "Organize e acompanhe seus projetos.",
                "Em desenvolvimento",
                False,
            ),
        )
        for index, (icon, label, status, description, button_text, enabled) in enumerate(menu_items):
            block = _PlatformMenuCard(
                icon,
                label,
                status,
                description,
                button_text,
                enabled,
                self._main_menu_widget,
            )
            block.setMinimumHeight(250)
            if enabled:
                block.activated.connect(self.open_lifeline_shell)
            self.menu_blocks.append(block)
            blocks_layout.addWidget(block, index // 2, index % 2)

        self.launcher_footer = QLabel("Mais sistemas serão disponibilizados em breve.")
        self.launcher_footer.setObjectName("launcher_footer")
        self.launcher_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        menu_layout.addWidget(self.launcher_footer)

        self._platform_stack.addWidget(self._main_menu_widget)
        self._platform_stack.addWidget(self.shell_widget)
        self.setCentralWidget(self._platform_stack)
        self._platform_stack.setCurrentWidget(self._main_menu_widget)
        self._set_shell_chrome_visible(False)

    def _set_shell_chrome_visible(self, visible: bool) -> None:
        """Exibe o chrome existente somente enquanto o shell está ativo."""
        self.menuBar().setVisible(visible)
        self.toolbar.setVisible(visible)
        self.statusBar().setVisible(visible)

    @property
    def is_main_menu_visible(self) -> bool:
        """Indica se a entrada principal está visível."""
        return self._platform_stack.currentWidget() is self._main_menu_widget

    @property
    def line_life_stage_labels(self) -> list[str]:
        """Nomes canônicos das cinco etapas reutilizadas pelo shell."""
        return list(self.LINE_LIFE_STAGE_LABELS)

    @property
    def stepper_current_index(self) -> int:
        """Índice da etapa projetada pelo tab atual; BOM não é uma etapa do stepper."""
        index = self.tabs.currentIndex()
        return index if 0 <= index < len(self.stepper_buttons) else -1

    def _update_stepper(self, index: int) -> None:
        """Sincroniza o estado visual do stepper com a única origem de abas."""
        current = index if 0 <= index < len(self.stepper_buttons) else -1
        for button_index, button in enumerate(self.stepper_buttons):
            button.setProperty("current", button_index == current)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def open_lifeline_shell(self) -> None:
        """Abre o shell existente da Linha de Vida sem recriar o projeto."""
        self._platform_stack.setCurrentWidget(self.shell_widget)
        self._set_shell_chrome_visible(True)

    def show_main_menu(self) -> None:
        """Retorna ao menu sem alterar projeto, licença ou abas do shell."""
        self._platform_stack.setCurrentWidget(self._main_menu_widget)
        self._set_shell_chrome_visible(False)

    def _build_tab_identification(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_id = QGroupBox("Identificação do Projeto")
        form_id = QFormLayout(grp_id)

        self.txt_title = QLineEdit()
        self.txt_title.textChanged.connect(self._on_field_changed)
        self.txt_client = QLineEdit()
        self.txt_client.textChanged.connect(self._on_field_changed)
        self.txt_location = QLineEdit()
        self.txt_location.textChanged.connect(self._on_field_changed)
        self.txt_engineer = QLineEdit()
        self.txt_engineer.textChanged.connect(self._on_field_changed)

        form_id.addRow("Título do Projeto:", self.txt_title)
        form_id.addRow("Cliente / Contratante:", self.txt_client)
        form_id.addRow("Local da Instalação:", self.txt_location)
        form_id.addRow("Engenheiro Responsável:", self.txt_engineer)

        layout.addWidget(grp_id)

        self.installation_widget = InstallationContainerWidget()
        self.installation_widget.changed.connect(self._on_field_changed)
        layout.addWidget(self.installation_widget)

        layout.addStretch()
        self.tabs.addTab(tab, "1. Identificação & Instalação")

    def _build_tab_geometry(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_controls = QGroupBox("Configuração de Postes e Vãos")
        h_ctrl = QHBoxLayout(grp_controls)

        # Botão de ajuda visual sobre postes e vãos
        btn_help_posts = ImageHelperButton("Anatomia de Postes e Vãos da Linha de Vida", "linha_horizontal.jpg")
        h_ctrl.addWidget(btn_help_posts)

        h_ctrl.addWidget(QLabel("Quantidade de Postes:"))
        self.spn_num_posts = QSpinBox()
        self.spn_num_posts.setRange(2, 30)
        self.spn_num_posts.setValue(2)
        self.spn_num_posts.valueChanged.connect(self._on_num_posts_changed)
        h_ctrl.addWidget(self.spn_num_posts)

        h_ctrl.addWidget(QLabel("Taxa Flecha Inicial (%f1):"))
        self.spn_sag_percent = QDoubleSpinBox()
        self.spn_sag_percent.setRange(1.0, 10.0)
        self.spn_sag_percent.setValue(3.0)
        self.spn_sag_percent.setSuffix(" %")
        self.spn_sag_percent.valueChanged.connect(self._on_sag_percent_changed)
        h_ctrl.addWidget(self.spn_sag_percent)

        h_ctrl.addWidget(QLabel("Vão Base:"))
        self.spn_equal_span = QDoubleSpinBox()
        self.spn_equal_span.setRange(1000.0, 50000.0)
        self.spn_equal_span.setValue(6600.0)
        self.spn_equal_span.setSuffix(" mm")
        h_ctrl.addWidget(self.spn_equal_span)

        btn_apply_equal = QPushButton("Aplicar Vãos Iguais")
        btn_apply_equal.setObjectName("btn_secondary")
        btn_apply_equal.clicked.connect(self._on_apply_equal_spans)
        h_ctrl.addWidget(btn_apply_equal)

        h_ctrl.addStretch()
        layout.addWidget(grp_controls)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Tabela de vãos
        self.table_spans = QTableWidget(1, 4)
        self.table_spans.setHorizontalHeaderLabels(["Vão", "Comprimento (mm)", "Comprimento (m)", "Flecha Inicial (mm)"])
        self.table_spans.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_spans.cellChanged.connect(self._on_span_table_cell_changed)
        splitter.addWidget(self.table_spans)

        # Canvas esquemático 2D
        grp_canvas = QGroupBox("Representação Esquemática da Linha de Vida (2D)")
        layout_canvas = QVBoxLayout(grp_canvas)
        self.canvas_2d = Lifeline2DCanvas()
        layout_canvas.addWidget(self.canvas_2d)
        splitter.addWidget(grp_canvas)

        layout.addWidget(splitter)
        self.tabs.addTab(tab, "2. Postes & Vãos (Geometria)")

    def _build_tab_users_load(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_users = QGroupBox("Critérios de Carregamento e Usuários (ABNT NBR 16325-2)")
        form_users = QFormLayout(grp_users)

        self.spn_total_users = QSpinBox()
        self.spn_total_users.setRange(1, 10)
        self.spn_total_users.setValue(1)
        self.spn_total_users.valueChanged.connect(self._on_users_changed)

        self.spn_simultaneous_users = QSpinBox()
        self.spn_simultaneous_users.setRange(1, 10)
        self.spn_simultaneous_users.setValue(1)
        self.spn_simultaneous_users.valueChanged.connect(self._on_users_changed)

        self.cmb_load_rule = QComboBox()
        self.cmb_load_rule.addItem("NBR 16325-2: 600 kgf (1º) + 100 kgf por adicional", LoadRuleType.NBR_16325_2.value)
        self.cmb_load_rule.addItem("Carga Customizada Livre (Divergência da Norma)", LoadRuleType.CUSTOM.value)
        self.cmb_load_rule.currentIndexChanged.connect(self._on_users_changed)

        self.spn_custom_load = QDoubleSpinBox()
        self.spn_custom_load.setRange(100.0, 50000.0)
        self.spn_custom_load.setValue(600.0)
        self.spn_custom_load.setSuffix(" kgf")
        self.spn_custom_load.setEnabled(False)
        self.spn_custom_load.valueChanged.connect(self._on_users_changed)

        self.lbl_calculated_load_banner = QLabel("Carga de Projeto Calculada: 600 kgf (~5.88 kN)")
        self.lbl_calculated_load_banner.setStyleSheet("font-weight: bold; color: #10b981; font-size: 14px;")

        self.lbl_rule_warning = QLabel("")
        self.lbl_rule_warning.setStyleSheet("color: #f59e0b; font-weight: bold;")
        self.lbl_rule_warning.setWordWrap(True)

        form_users.addRow("Usuários Cadastrados:", self.spn_total_users)
        form_users.addRow("Usuários Simultâneos em Queda:", self.spn_simultaneous_users)
        form_users.addRow("Regra de Combinação:", self.cmb_load_rule)
        form_users.addRow("Carga Total Customizada:", self.spn_custom_load)
        form_users.addRow("", self.lbl_calculated_load_banner)
        form_users.addRow("", self.lbl_rule_warning)

        layout.addWidget(grp_users)

        # Zona Livre de Queda (NR-35) com botões de imagens explicativas integrados
        grp_zlq = QGroupBox("Zona Livre de Queda - ZLQ (NR-35)")
        form_zlq = QFormLayout(grp_zlq)

        # Header da ZLQ com botão para ver o diagrama completo ZLQ
        h_zlq_header = QHBoxLayout()
        lbl_zlq_info = QLabel("Cálculo da distância vertical necessária para retenção segura da queda:")
        btn_zlq_master = ImageHelperButton("Diagrama Geral da Zona Livre de Queda (NR-35)", "zlq.jpg")
        h_zlq_header.addWidget(lbl_zlq_info)
        h_zlq_header.addWidget(btn_zlq_master)
        h_zlq_header.addStretch()
        form_zlq.addRow("", h_zlq_header)

        # 1. Talabarte
        self.spn_lanyard = QDoubleSpinBox()
        self.spn_lanyard.setRange(0.5, 3.0)
        self.spn_lanyard.setValue(1.5)
        self.spn_lanyard.setSuffix(" m")
        self.spn_lanyard.valueChanged.connect(self._on_field_changed)
        form_zlq.addRow("Comprimento do Talabarte:", self.spn_lanyard)

        # 2. Absorvedor com botão de imagem
        h_abs = QHBoxLayout()
        self.spn_absorber = QDoubleSpinBox()
        self.spn_absorber.setRange(0.0, 2.0)
        self.spn_absorber.setValue(1.2)
        self.spn_absorber.setSuffix(" m")
        self.spn_absorber.valueChanged.connect(self._on_field_changed)
        btn_help_abs = ImageHelperButton("Extensão do Absorvedor de Energia (Fechado vs Aberto)", "absorvedor_energia.jpg")
        h_abs.addWidget(self.spn_absorber)
        h_abs.addWidget(btn_help_abs)
        form_zlq.addRow("Extensão do Absorvedor de Energia:", h_abs)

        # 3. Deslocamento do Cinto / Altura do Usuário com botão de imagem
        h_worker = QHBoxLayout()
        self.spn_worker_offset = QDoubleSpinBox()
        self.spn_worker_offset.setRange(1.0, 2.5)
        self.spn_worker_offset.setValue(1.5)
        self.spn_worker_offset.setSuffix(" m")
        self.spn_worker_offset.valueChanged.connect(self._on_field_changed)
        btn_help_worker = ImageHelperButton("Deslocamento do Cinto e Altura do Usuário", "altura_usuario_cinto.jpg")
        h_worker.addWidget(self.spn_worker_offset)
        h_worker.addWidget(btn_help_worker)
        form_zlq.addRow("Deslocamento do Cinto / Altura do Usuário:", h_worker)

        # 4. Margem de segurança
        self.spn_safety_margin = QDoubleSpinBox()
        self.spn_safety_margin.setRange(0.5, 3.0)
        self.spn_safety_margin.setValue(1.0)
        self.spn_safety_margin.setSuffix(" m")
        self.spn_safety_margin.valueChanged.connect(self._on_field_changed)
        form_zlq.addRow("Margem de Segurança Obrigatória (NR-35):", self.spn_safety_margin)

        # 5. Altura Disponível com botão de imagem
        h_avail = QHBoxLayout()
        self.spn_available_h = QDoubleSpinBox()
        self.spn_available_h.setRange(0.0, 100.0)
        self.spn_available_h.setValue(6.5)
        self.spn_available_h.setSuffix(" m")
        self.spn_available_h.valueChanged.connect(self._on_field_changed)
        btn_help_avail = ImageHelperButton("Altura Livre Disponível no Local (Hdisp)", "altura_livre_disponivel.jpg")
        h_avail.addWidget(self.spn_available_h)
        h_avail.addWidget(btn_help_avail)
        form_zlq.addRow("Altura Livre Disponível no Local (Hdisp):", h_avail)

        layout.addWidget(grp_zlq)
        layout.addStretch()
        self.tabs.addTab(tab, "3. Usuários, Cargas & ZLQ")

    def _build_tab_cable(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        grp_sel = QGroupBox("Catálogo NBR ISO 2408")
        form_sel = QFormLayout(grp_sel)

        self.cmb_cable_spec = QComboBox()
        self.cmb_cable_spec.currentIndexChanged.connect(self._on_cable_spec_changed)
        form_sel.addRow("Especificação do Cabo:", self.cmb_cable_spec)
        layout.addWidget(grp_sel)

        grp_props = QGroupBox("Propriedades Mecânicas e Físicas do Cabo Selecionado")
        grid = QGridLayout(grp_props)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(10)

        self.lbl_cable_d = QLabel("-")
        self.lbl_cable_core = QLabel("-")
        self.lbl_cable_factor = QLabel("-")
        self.lbl_cable_am = QLabel("-")
        self.lbl_cable_e = QLabel("-")
        self.lbl_cable_fu = QLabel("-")

        for lbl in [self.lbl_cable_d, self.lbl_cable_core, self.lbl_cable_factor, self.lbl_cable_am, self.lbl_cable_e, self.lbl_cable_fu]:
            lbl.setStyleSheet("font-weight: bold; color: #ffffff;")

        grid.addWidget(QLabel("Diâmetro Nominal (d):"), 0, 0)
        grid.addWidget(self.lbl_cable_d, 0, 1)

        grid.addWidget(QLabel("Tipo de Alma:"), 0, 2)
        grid.addWidget(self.lbl_cable_core, 0, 3)

        grid.addWidget(QLabel("Fator de Área Metálica (F):"), 1, 0)
        grid.addWidget(self.lbl_cable_factor, 1, 1)

        grid.addWidget(QLabel("Área Metálica (Am):"), 1, 2)
        grid.addWidget(self.lbl_cable_am, 1, 3)

        grid.addWidget(QLabel("Módulo de Elasticidade (E):"), 2, 0)
        grid.addWidget(self.lbl_cable_e, 2, 1)

        grid.addWidget(QLabel("Força Mínima de Ruptura (Fu):"), 2, 2)
        grid.addWidget(self.lbl_cable_fu, 2, 3)

        layout.addWidget(grp_props)
        layout.addStretch()
        self.tabs.addTab(tab, "4. Cabo de Aço")

    def _build_tab_results(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.grp_verdict = QGroupBox("Veredito")
        self.grp_verdict.setObjectName("verdict_panel")
        verdict_layout = QVBoxLayout(self.grp_verdict)
        self.lbl_verdict = QLabel("Aguardando cálculo")
        self.lbl_verdict.setObjectName("verdict_label")
        self.lbl_verdict.setAccessibleName("Veredito do dimensionamento")
        verdict_layout.addWidget(self.lbl_verdict)
        layout.addWidget(self.grp_verdict)

        # Cards de Indicadores
        self.grp_kpi = QGroupBox("KPIs — Indicadores de desempenho e segurança")
        grid_kpi = QGridLayout(self.grp_kpi)

        self.card_tension = self._create_kpi_card("Tração Máx. Ancoragem", "-", "#38bdf8")
        self.card_fs = self._create_kpi_card("Fator de Segurança", "-", "#10b981")
        self.card_sag = self._create_kpi_card("Flecha Dinâmica (f2)", "-", "#f59e0b")
        self.card_zlq = self._create_kpi_card("ZLQ Requerida", "-", "#a855f7")

        grid_kpi.addWidget(self.card_tension, 0, 0)
        grid_kpi.addWidget(self.card_fs, 0, 1)
        grid_kpi.addWidget(self.card_sag, 0, 2)
        grid_kpi.addWidget(self.card_zlq, 0, 3)

        layout.addWidget(self.grp_kpi)

        # Tabela de Resultados por Vão
        grp_span_res = QGroupBox("Resultados Detalhados por Vão")
        layout_span_res = QVBoxLayout(grp_span_res)
        self.table_results = QTableWidget(1, 7)
        self.table_results.setHorizontalHeaderLabels([
            "Vão", "Comprimento (mm)", "Alongamento (mm)", "Flecha f2 (mm)", "Tração (kgf)", "Fator Segurança", "Status"
        ])
        self.table_results.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout_span_res.addWidget(self.table_results)
        layout.addWidget(grp_span_res)

        # Box de Auditoria e Advertências
        h_audit = QHBoxLayout()

        self.grp_audit = QGroupBox("Auditoria do Solucionador Numérico")
        self.grp_audit.setCheckable(True)
        self.grp_audit.setChecked(True)
        self.grp_audit.toggled.connect(
            lambda checked: self._set_group_content_visible(self.grp_audit, checked)
        )
        form_audit = QFormLayout(self.grp_audit)
        self.lbl_audit_method = QLabel("Método da Bisseção com Refinamento")
        self.lbl_audit_iter = QLabel("-")
        self.lbl_audit_res = QLabel("-")
        self.lbl_audit_tol = QLabel("0,000001 kgf (1,0 × 10⁻⁶ kgf / 0,001 g)")
        self.lbl_audit_res.setStyleSheet("font-weight: bold; color: #10b981;")
        self.lbl_audit_tol.setStyleSheet("font-weight: bold; color: #94a3b8;")

        form_audit.addRow("Algoritmo Numérico:", self.lbl_audit_method)
        form_audit.addRow("Iterações Executadas:", self.lbl_audit_iter)
        form_audit.addRow("Erro Residual:", self.lbl_audit_res)
        form_audit.addRow("Tolerância Adotada:", self.lbl_audit_tol)
        h_audit.addWidget(self.grp_audit, 1)

        self.grp_problems = QGroupBox("Problemas — advertências e pendências")
        self.grp_problems.setCheckable(True)
        self.grp_problems.setChecked(True)
        self.grp_problems.toggled.connect(
            lambda checked: self._set_group_content_visible(self.grp_problems, checked)
        )
        layout_warn = QVBoxLayout(self.grp_problems)
        self.txt_warnings = QTextEdit()
        self.txt_warnings.setReadOnly(True)
        layout_warn.addWidget(self.txt_warnings)
        h_audit.addWidget(self.grp_problems, 2)

        layout.addLayout(h_audit)

        # Botão inferior de geração de PDF
        h_btn_pdf = QHBoxLayout()
        h_btn_pdf.addStretch()
        self.btn_pdf_tab = QPushButton("📄 Emitir Memória de Cálculo Estrutural em PDF")
        self.btn_pdf_tab.setObjectName("btn_pdf")
        self.btn_pdf_tab.clicked.connect(self._on_action_generate_pdf)
        h_btn_pdf.addWidget(self.btn_pdf_tab)
        layout.addLayout(h_btn_pdf)

        self.tabs.addTab(tab, "5. Resultados & Auditoria")

    def _build_tab_bom(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Barra de status da BOM e Ações
        grp_bom_status = QGroupBox("Status de Liberação dos Materiais")
        h_status = QHBoxLayout(grp_bom_status)
        h_status.setContentsMargins(10, 10, 10, 10)

        self.lbl_bom_status = QLabel("🔒 BLOQUEADO — Exige Memória de Cálculo Aprovada e ART da Estrutura")
        self.lbl_bom_status.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 13px;")
        h_status.addWidget(self.lbl_bom_status)

        h_status.addStretch()

        self.btn_refresh_bom = QPushButton("🔄 Atualizar Quantitativo")
        self.btn_refresh_bom.setObjectName("btn_secondary")
        self.btn_refresh_bom.clicked.connect(self._refresh_bom_tab)
        h_status.addWidget(self.btn_refresh_bom)

        self.btn_export_bom_excel = QPushButton("📊 Exportar BOM para Excel (.xlsx)")
        self.btn_export_bom_excel.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
            }
        """)
        self.btn_export_bom_excel.clicked.connect(self._on_action_export_bom_excel)
        self.btn_export_bom_excel.setEnabled(False)
        h_status.addWidget(self.btn_export_bom_excel)

        layout.addWidget(grp_bom_status)

        # Cards com Resumo Quantitativo
        h_cards = QHBoxLayout()
        self.card_bom_cable = self._create_kpi_card("Metragem de Cabo (c/ Sobras)", "-", "#38bdf8")
        self.card_bom_posts = self._create_kpi_card("Total de Postes", "-", "#38bdf8")
        self.card_bom_items = self._create_kpi_card("Total de Componentes", "-", "#a78bfa")
        self.card_bom_fix = self._create_kpi_card("Tipo de Fixação", "-", "#10b981")

        h_cards.addWidget(self.card_bom_cable)
        h_cards.addWidget(self.card_bom_posts)
        h_cards.addWidget(self.card_bom_items)
        h_cards.addWidget(self.card_bom_fix)
        layout.addLayout(h_cards)

        # Tabela Detalhada de Materiais
        self.table_bom = QTableWidget(0, 8)
        self.table_bom.setHorizontalHeaderLabels([
            "Item", "Código", "Categoria", "Componente", "Especificação Técnica", "Qtd.", "Un.", "Instruções de Montagem"
        ])
        self.table_bom.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table_bom.horizontalHeader().setStretchLastSection(True)
        self.table_bom.setColumnWidth(0, 50)
        self.table_bom.setColumnWidth(1, 90)
        self.table_bom.setColumnWidth(2, 135)
        self.table_bom.setColumnWidth(3, 190)
        self.table_bom.setColumnWidth(4, 250)
        self.table_bom.setColumnWidth(5, 70)
        self.table_bom.setColumnWidth(6, 50)
        self.table_bom.setAlternatingRowColors(True)
        self.table_bom.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_bom.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        layout.addWidget(self.table_bom)

        self.tabs.addTab(tab, "6. Lista de Materiais (BOM)")

    def _create_kpi_card(self, title: str, initial_val: str, color_hex: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background-color: #1a1a22; border: 1px solid #333340; border-radius: 6px; padding: 10px;"
        )
        l = QVBoxLayout(card)
        l.setContentsMargins(4, 4, 4, 4)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: bold;")
        lbl_v = QLabel(initial_val)
        lbl_v.setObjectName("val")
        lbl_v.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color_hex};")
        l.addWidget(lbl_t)
        l.addWidget(lbl_v)
        return card

    def _update_kpi_value(self, card: QFrame, val_text: str, color_hex: Optional[str] = None) -> None:
        lbl_val = card.findChild(QLabel, "val")
        if lbl_val:
            lbl_val.setText(val_text)
            if color_hex:
                lbl_val.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color_hex};")

    def _populate_cables_dropdown(self) -> None:
        prev_updating = self._updating_ui
        self._updating_ui = True
        try:
            self.cmb_cable_spec.clear()
            cables = self.service.catalog.list_all()
            for c in cables:
                self.cmb_cable_spec.addItem(c.specification, c.specification)
        finally:
            self._updating_ui = prev_updating

    def _on_field_changed(self) -> None:
        if self._updating_ui or getattr(self.current_project, "is_read_only", False):
            return
        self._sync_ui_to_project()
        self._update_status_badge()

    def _on_cable_spec_changed(self) -> None:
        spec = self.cmb_cable_spec.currentText()
        if not spec:
            return
        cabo = self.service.catalog.get_by_specification(spec)
        if cabo:
            self.lbl_cable_d.setText(f"{cabo.diameter_mm:.1f} mm")
            self.lbl_cable_core.setText(cabo.core_type)
            self.lbl_cable_factor.setText(f"{cabo.metallic_area_factor:.3f}")
            self.lbl_cable_am.setText(f"{cabo.metallic_area_mm2:.2f} mm²")
            self.lbl_cable_e.setText(f"{cabo.elastic_modulus_kgf_mm2:,.0f} kgf/mm²")
            self.lbl_cable_fu.setText(f"{cabo.min_breaking_load_kgf:,.2f} kgf ({cabo.min_breaking_load_kn:.2f} kN)")
            if not self._updating_ui and not getattr(self.current_project, "is_read_only", False):
                if self.current_project.cable != cabo:
                    self.current_project.update_cable(cabo)
                    self._update_status_badge()

    def _on_num_posts_changed(self, num_posts: int) -> None:
        if self._updating_ui or getattr(self.current_project, "is_read_only", False):
            return
        num_spans = num_posts - 1
        current_spans = list(self.current_project.spans)
        sag_pct = self.spn_sag_percent.value()
        base_span = self.spn_equal_span.value()

        new_spans: List[SpanGeometry] = []
        for i in range(num_spans):
            if i < len(current_spans):
                new_spans.append(SpanGeometry(span_index=i + 1, span_mm=current_spans[i].span_mm, initial_sag_percent=sag_pct))
            else:
                new_spans.append(SpanGeometry(span_index=i + 1, span_mm=base_span, initial_sag_percent=sag_pct))

        if not self._commit_span_changes(new_spans):
            return
        self._refresh_span_table()
        self._update_canvas()
        self._update_status_badge()

    def _on_sag_percent_changed(self, sag_pct: float) -> None:
        if self._updating_ui or getattr(self.current_project, "is_read_only", False):
            return
        new_spans = [
            SpanGeometry(span_index=s.span_index, span_mm=s.span_mm, initial_sag_percent=sag_pct)
            for s in self.current_project.spans
        ]
        if not self._commit_span_changes(new_spans):
            return
        self._refresh_span_table()
        self._update_canvas()
        self._update_status_badge()

    def _on_apply_equal_spans(self) -> None:
        if self._updating_ui or getattr(self.current_project, "is_read_only", False):
            return
        base_val = self.spn_equal_span.value()
        sag_pct = self.spn_sag_percent.value()
        new_spans = [
            SpanGeometry(span_index=i + 1, span_mm=base_val, initial_sag_percent=sag_pct)
            for i in range(len(self.current_project.spans))
        ]
        if not self._commit_span_changes(new_spans):
            return
        self._refresh_span_table()
        self._update_canvas()
        self._update_status_badge()

    def _on_span_table_cell_changed(self, row: int, col: int) -> None:
        if self._updating_ui or col != 1 or getattr(self.current_project, "is_read_only", False):
            return
        item = self.table_spans.item(row, col)
        if not item:
            return
        try:
            val_mm = float(item.text().strip().replace(",", "."))
            if val_mm <= 0:
                return
            current_spans = list(self.current_project.spans)
            if row < len(current_spans):
                sag_pct = current_spans[row].initial_sag_percent
                current_spans[row] = SpanGeometry(span_index=row + 1, span_mm=val_mm, initial_sag_percent=sag_pct)
                if not self._commit_span_changes(current_spans):
                    return
                self._refresh_span_table(skip_edit_row=row)
                self._update_canvas()
                self._update_status_badge()
        except ValueError:
            pass

    def _commit_span_changes(self, spans: List[SpanGeometry]) -> bool:
        """Valida mudanças geométricas e restaura os controles se o tier bloquear."""
        try:
            self.service.update_project_spans(self.current_project, spans)
            return True
        except PermissionError as exc:
            previous_updating_state = self._updating_ui
            self._updating_ui = True
            try:
                lic = self.license_manager.get_license()
                max_posts = lic.max_allowed_spans + 1
                if self.current_project.is_read_only:
                    max_posts = max(max_posts, len(self.current_project.spans) + 1)
                self.spn_num_posts.setRange(2, max_posts)
                self.spn_num_posts.setValue(len(self.current_project.spans) + 1)
                if self.current_project.spans:
                    self.spn_sag_percent.setValue(self.current_project.spans[0].initial_sag_percent)
                    self.spn_equal_span.setValue(self.current_project.spans[0].span_mm)
                self._refresh_span_table()
                self._update_canvas()
            finally:
                self._updating_ui = previous_updating_state
            QMessageBox.warning(self, "Limite de Vãos do Plano", str(exc))
            return False

    def _on_users_changed(self) -> None:
        rule_val = self.cmb_load_rule.currentData()
        is_custom = (rule_val == LoadRuleType.CUSTOM.value)
        if not getattr(self.current_project, "is_read_only", False):
            self.spn_custom_load.setEnabled(is_custom)

        user_cfg = UserLoadConfig(
            total_users=self.spn_total_users.value(),
            simultaneous_users=self.spn_simultaneous_users.value(),
            rule_type=LoadRuleType(rule_val),
            custom_total_load_kgf=self.spn_custom_load.value() if is_custom else None,
        )

        load_kgf = user_cfg.calculated_design_load_kgf
        load_kn = (load_kgf * 9.80665) / 1000.0
        self.lbl_calculated_load_banner.setText(f"Carga de Projeto Calculada: {load_kgf:.1f} kgf (~{load_kn:.2f} kN)")

        if user_cfg.warning_text:
            self.lbl_rule_warning.setText(user_cfg.warning_text)
            self.lbl_rule_warning.setStyleSheet("color: #f59e0b; font-weight: bold;")
        else:
            self.lbl_rule_warning.setText("✓ Conforme critérios da ABNT NBR 16325-2.")
            self.lbl_rule_warning.setStyleSheet("color: #10b981; font-weight: bold;")

        if not self._updating_ui and not getattr(self.current_project, "is_read_only", False):
            self.current_project.update_user_config(user_cfg)
            self._update_status_badge()

    def _refresh_span_table(self, skip_edit_row: int = -1) -> None:
        prev_updating = self._updating_ui
        self._updating_ui = True
        try:
            self.table_spans.setRowCount(len(self.current_project.spans))
            for i, s in enumerate(self.current_project.spans):
                item_idx = QTableWidgetItem(f"Vão {s.span_index}")
                item_idx.setFlags(item_idx.flags() & ~Qt.ItemFlag.ItemIsEditable)

                if i != skip_edit_row:
                    item_mm = QTableWidgetItem(f"{s.span_mm:.0f}")
                    self.table_spans.setItem(i, 1, item_mm)

                item_m = QTableWidgetItem(f"{s.span_mm / 1000.0:.2f}")
                item_m.setFlags(item_m.flags() & ~Qt.ItemFlag.ItemIsEditable)

                f1_val = s.span_mm * (s.initial_sag_percent / 100.0)
                item_f1 = QTableWidgetItem(f"{f1_val:.1f}")
                item_f1.setFlags(item_f1.flags() & ~Qt.ItemFlag.ItemIsEditable)

                self.table_spans.setItem(i, 0, item_idx)
                self.table_spans.setItem(i, 2, item_m)
                self.table_spans.setItem(i, 3, item_f1)
        finally:
            self._updating_ui = prev_updating

    def _update_canvas(self) -> None:
        crit_idx = 1
        dyn_f2 = 0.0
        if self.current_project.calculation_result:
            crit_idx = self.current_project.calculation_result.critical_span_index
            dyn_f2 = self.current_project.calculation_result.critical_span_result.dynamic_sag_mm
        self.canvas_2d.set_geometry(self.current_project.spans, crit_idx, dyn_f2)

    def _sync_ui_to_project(self) -> None:
        if getattr(self.current_project, "is_read_only", False):
            return
        self.current_project.title = self.txt_title.text().strip()
        self.current_project.client = self.txt_client.text().strip()
        self.current_project.location = self.txt_location.text().strip()
        self.current_project.responsible_engineer = self.txt_engineer.text().strip()

        self.current_project.installation = self.installation_widget.get_installation()

        avail_h = self.spn_available_h.value()
        self.current_project.clearance_input = FallClearanceInput(
            lanyard_length_m=self.spn_lanyard.value(),
            absorber_extension_m=self.spn_absorber.value(),
            worker_height_offset_m=self.spn_worker_offset.value(),
            safety_margin_m=self.spn_safety_margin.value(),
            available_clearance_m=avail_h if avail_h > 0 else None,
        )

        self.lbl_project_title_display.setText(self.current_project.title or "Sem Título")

    def _apply_read_only_ui(self, is_read_only: bool) -> None:
        """Ajusta o estado de edição da interface conforme o modo somente leitura."""
        lic = self.license_manager.get_license()

        # Identificação
        self.txt_title.setReadOnly(is_read_only)
        self.txt_client.setReadOnly(is_read_only)
        self.txt_location.setReadOnly(is_read_only)
        self.txt_engineer.setReadOnly(is_read_only)
        self.installation_widget.setEnabled(not is_read_only)

        # Postes e vãos
        self.spn_num_posts.setEnabled(not is_read_only)
        max_posts = lic.max_allowed_spans + 1
        if is_read_only:
            max_posts = max(max_posts, len(self.current_project.spans) + 1)
        self.spn_num_posts.setRange(2, max_posts)

        self.spn_sag_percent.setEnabled(not is_read_only)
        self.spn_equal_span.setEnabled(not is_read_only)
        self.table_spans.setEnabled(not is_read_only)

        # Usuários e carregamento
        self.spn_total_users.setEnabled(not is_read_only)
        self.spn_simultaneous_users.setEnabled(not is_read_only)
        self.cmb_load_rule.setEnabled(not is_read_only)
        is_custom = (self.cmb_load_rule.currentData() == LoadRuleType.CUSTOM.value)
        self.spn_custom_load.setEnabled(not is_read_only and is_custom)

        # ZLQ
        self.spn_lanyard.setEnabled(not is_read_only)
        self.spn_absorber.setEnabled(not is_read_only)
        self.spn_worker_offset.setEnabled(not is_read_only)
        self.spn_safety_margin.setEnabled(not is_read_only)
        self.spn_available_h.setEnabled(not is_read_only)

        # Cabo
        self.cmb_cable_spec.setEnabled(not is_read_only)

        # Botões de contexto e ações
        self.btn_save.setEnabled(not is_read_only)
        self.btn_calculate.setEnabled(not is_read_only)
        if hasattr(self, "act_calc"):
            self.act_calc.setEnabled(not is_read_only)
        if hasattr(self, "act_save"):
            self.act_save.setEnabled(not is_read_only)
        if hasattr(self, "act_save_as"):
            self.act_save_as.setEnabled(not is_read_only)
        if hasattr(self, "act_clone"):
            self.act_clone.setEnabled(not is_read_only)

        # Restrições de saída por licença (PDF, BOM, Impressão)
        pdf_enabled = (not is_read_only) and lic.is_pdf_allowed
        bom_enabled = (not is_read_only) and lic.is_bom_allowed
        print_enabled = (not is_read_only) and lic.is_print_allowed

        if hasattr(self, "btn_generate_pdf"):
            self.btn_generate_pdf.setEnabled(pdf_enabled)
        if hasattr(self, "btn_pdf_tab"):
            self.btn_pdf_tab.setEnabled(pdf_enabled)
        if hasattr(self, "act_pdf"):
            self.act_pdf.setEnabled(pdf_enabled)
        if hasattr(self, "act_bom"):
            self.act_bom.setEnabled(bom_enabled)
        if hasattr(self, "act_print"):
            self.act_print.setEnabled(print_enabled)

    def load_project_to_ui(self, project: Project) -> None:
        self._updating_ui = True
        try:
            self.current_project = project

            self.txt_title.setText(project.title)
            self.txt_client.setText(project.client)
            self.txt_location.setText(project.location)
            self.txt_engineer.setText(project.responsible_engineer)
            self.lbl_project_title_display.setText(project.title)

            self.installation_widget.set_installation(project.installation)

            lic = self.license_manager.get_license()
            max_posts = lic.max_allowed_spans + 1
            if project.is_read_only:
                max_posts = max(max_posts, len(project.spans) + 1)
            self.spn_num_posts.setRange(2, max_posts)
            self.spn_num_posts.setValue(len(project.spans) + 1)
            if project.spans:
                self.spn_sag_percent.setValue(project.spans[0].initial_sag_percent)
                self.spn_equal_span.setValue(project.spans[0].span_mm)

            u_cfg = project.user_config
            self.spn_total_users.setValue(u_cfg.total_users)
            self.spn_simultaneous_users.setValue(u_cfg.simultaneous_users)
            idx_rule = self.cmb_load_rule.findData(u_cfg.rule_type.value)
            if idx_rule >= 0:
                self.cmb_load_rule.setCurrentIndex(idx_rule)
            if u_cfg.custom_total_load_kgf:
                self.spn_custom_load.setValue(u_cfg.custom_total_load_kgf)
            self.spn_custom_load.setEnabled(u_cfg.rule_type == LoadRuleType.CUSTOM and not project.is_read_only)

            cl = project.clearance_input
            self.spn_lanyard.setValue(cl.lanyard_length_m)
            self.spn_absorber.setValue(cl.absorber_extension_m)
            self.spn_worker_offset.setValue(cl.worker_height_offset_m)
            self.spn_safety_margin.setValue(cl.safety_margin_m)
            self.spn_available_h.setValue(cl.available_clearance_m or 0.0)

            if project.cable:
                idx_c = self.cmb_cable_spec.findText(project.cable.specification)
                if idx_c >= 0:
                    self.cmb_cable_spec.setCurrentIndex(idx_c)

            self._refresh_span_table()
            self._on_cable_spec_changed()
            self._on_users_changed()
            self._update_results_tab()
            self._update_canvas()
            self._apply_read_only_ui(project.is_read_only)
            self._update_status_badge()
        finally:
            self._updating_ui = False

    def _update_status_badge(self) -> None:
        self._update_verdict_from_state()
        if self.current_project.is_read_only:
            self.lbl_status_badge.setText("🔒 SOMENTE LEITURA")
            self.lbl_status_badge.setStyleSheet(
                "background-color: #475569; color: #f8fafc; padding: 4px 12px; border-radius: 4px; font-weight: bold;"
            )
            self._refresh_bom_tab()
            return

        st = self.current_project.status
        if st == ProjectStatus.CALCULATED_VALID:
            self.lbl_status_badge.setText("✓ APROVADO")
            self.lbl_status_badge.setStyleSheet("background-color: #059669; color: #ffffff; padding: 4px 12px; border-radius: 4px; font-weight: bold;")
        elif st == ProjectStatus.CALCULATED_REJECTED:
            self.lbl_status_badge.setText("✗ REPROVADO")
            self.lbl_status_badge.setStyleSheet("background-color: #dc2626; color: #ffffff; padding: 4px 12px; border-radius: 4px; font-weight: bold;")
        elif st == ProjectStatus.INVALIDATED:
            self.lbl_status_badge.setText("⚠ ALTERADO (RECÁLCULO NECESSÁRIO)")
            self.lbl_status_badge.setStyleSheet("background-color: #d97706; color: #ffffff; padding: 4px 12px; border-radius: 4px; font-weight: bold;")
        else:
            self.lbl_status_badge.setText("RASCUNHO")
            self.lbl_status_badge.setStyleSheet("background-color: #475569; color: #ffffff; padding: 4px 12px; border-radius: 4px; font-weight: bold;")
        self._refresh_bom_tab()

    def _update_verdict_from_state(self) -> None:
        """Apresenta somente o veredito já produzido pelo estado do projeto."""
        status = self.current_project.status
        has_result = self.current_project.calculation_result is not None
        if status == ProjectStatus.CALCULATED_VALID and has_result:
            text = "Aprovado — dimensionamento conforme os resultados calculados"
            state = "approved"
        elif status == ProjectStatus.CALCULATED_REJECTED and has_result:
            text = "Reprovado — revise os problemas indicados"
            state = "rejected"
        elif status == ProjectStatus.INVALIDATED:
            text = "Dados alterados — recálculo necessário"
            state = "changed"
        else:
            text = "Aguardando cálculo"
            state = "pending"
        self.lbl_verdict.setText(text)
        self.lbl_verdict.setProperty("state", state)
        self.lbl_verdict.style().unpolish(self.lbl_verdict)
        self.lbl_verdict.style().polish(self.lbl_verdict)
        self.lbl_verdict.update()

    def _on_action_calculate(self) -> None:
        if self.current_project.is_read_only:
            QMessageBox.warning(
                self,
                "Recálculo Bloqueado",
                "Projetos abertos em modo somente leitura (múltiplos vãos sob licença Free) não podem ser recalculados.<br/><br/>"
                "Para dimensionar múltiplos vãos, ative uma licença modo local de revisão."
            )
            return
        self._sync_ui_to_project()
        try:
            self.service.calculate_project(self.current_project)
            self._update_results_tab()
            self._update_canvas()
            self._update_status_badge()
            self.tabs.setCurrentIndex(4)
            self.statusBar().showMessage("Cálculo concluído com sucesso.", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Erro de Cálculo", f"Falha ao executar o cálculo: {str(e)}")

    def _set_group_content_visible(self, group: QGroupBox, visible: bool) -> None:
        """Expande ou recolhe apenas o conteúdo, preservando o cabeçalho do grupo."""
        group_layout = group.layout()
        if group_layout is None:
            return
        for index in range(group_layout.count()):
            item = group_layout.itemAt(index)
            widget = item.widget()
            if widget is not None:
                widget.setVisible(visible)
            elif item.layout() is not None:
                item.layout().setEnabled(visible)

    def _update_results_tab(self) -> None:
        self._update_verdict_from_state()
        res = self.current_project.calculation_result
        if not res:
            self._update_kpi_value(self.card_tension, "-")
            self._update_kpi_value(self.card_fs, "-")
            self._update_kpi_value(self.card_sag, "-")
            self._update_kpi_value(self.card_zlq, "-")
            self.table_results.setRowCount(0)
            self.lbl_audit_iter.setText("-")
            self.lbl_audit_res.setText("-")
            self.txt_warnings.setHtml("<span style='color: #94a3b8;'>Nenhum cálculo recente executado.</span>")
            return

        crit = res.critical_span_result

        # KPI 1: Tração
        t_kn = (res.end_anchor_load_kgf * 9.80665) / 1000.0
        self._update_kpi_value(self.card_tension, f"{res.end_anchor_load_kgf:,.0f} kgf ({t_kn:.2f} kN)")

        # KPI 2: FS
        fs_color = "#10b981" if crit.safety_factor >= 2.0 else "#ef4444"
        self._update_kpi_value(self.card_fs, f"{crit.safety_factor:.3f} (Mín: 2.0)", fs_color)

        # KPI 3: Flecha
        self._update_kpi_value(self.card_sag, f"{crit.dynamic_sag_mm:.1f} mm ({crit.dynamic_sag_mm/1000:.2f} m)")

        # KPI 4: ZLQ
        if crit.clearance_result:
            zlq_text = f"{crit.clearance_result.required_clearance_m:.2f} m"
            zlq_color = "#ef4444" if crit.clearance_result.collision_risk else "#10b981"
            self._update_kpi_value(self.card_zlq, zlq_text, zlq_color)
        else:
            self._update_kpi_value(self.card_zlq, "-")

        # Tabela detalhada por vão
        self.table_results.setRowCount(len(res.span_results))
        for i, s_res in enumerate(res.span_results):
            span_geom = self.current_project.spans[i]
            is_crit = (i + 1 == res.critical_span_index)
            lbl_span = f"Vão {i + 1}" + (" (★ Crítico)" if is_crit else "")

            self.table_results.setItem(i, 0, QTableWidgetItem(lbl_span))
            self.table_results.setItem(i, 1, QTableWidgetItem(f"{span_geom.span_mm:,.0f}"))
            self.table_results.setItem(i, 2, QTableWidgetItem(f"{s_res.elongation_mm:.2f}"))
            self.table_results.setItem(i, 3, QTableWidgetItem(f"{s_res.dynamic_sag_mm:.2f}"))
            self.table_results.setItem(i, 4, QTableWidgetItem(f"{s_res.tension_kgf:,.1f}"))
            self.table_results.setItem(i, 5, QTableWidgetItem(f"{s_res.safety_factor:.3f}"))
            st_item = QTableWidgetItem(s_res.status_text)
            if s_res.is_approved:
                st_item.setForeground(QColor("#10b981"))
            else:
                st_item.setForeground(QColor("#ef4444"))
            self.table_results.setItem(i, 6, st_item)

        # Auditoria Numérica com valores decimais exatos e gramas (Ajuste 2)
        lic = self.license_manager.get_license()
        if not lic.is_memory_allowed:
            self.lbl_audit_iter.setText("🔒 Disponível no modo local de revisão")
            self.lbl_audit_res.setText("🔒 Disponível no modo local de revisão")
            self.lbl_audit_tol.setText("0,000001 kgf (0,001 g — 10⁻⁶ kgf)")
        else:
            err_kgf = crit.residual_error_kgf
            err_grams = err_kgf * 1000.0
            self.lbl_audit_iter.setText(f"{crit.iterations} iterações (Convergência Garantida)")
            self.lbl_audit_res.setText(f"{err_kgf:.8f} kgf ({err_grams:.5f} g) — Exato")
            self.lbl_audit_tol.setText("0,000001 kgf (0,001 g — 10⁻⁶ kgf)")

        # Advertências e Pendências com Alto Contraste HTML (Ajuste 1)
        html_blocks = []
        if res.warnings:
            html_blocks.append("<div style='color: #fbbf24; font-weight: bold; font-size: 13px; margin-bottom: 4px;'>⚠️ ADVERTÊNCIAS TÉCNICAS E NORMATIVAS:</div>")
            for w in res.warnings:
                html_blocks.append(f"<div style='color: #f1f5f9; margin-left: 10px; margin-bottom: 6px;'>• {w}</div>")

        gaps = self.current_project.installation.get_structural_gaps()
        if gaps:
            html_blocks.append("<div style='color: #f87171; font-weight: bold; font-size: 13px; margin-top: 10px; margin-bottom: 4px;'>⛔ PENDÊNCIAS ESTRUTURAIS (BLOQUEIO DE APROVAÇÃO):</div>")
            for g in gaps:
                html_blocks.append(f"<div style='color: #fca5a5; margin-left: 10px; margin-bottom: 6px;'>• {g}</div>")

        if not html_blocks:
            html_blocks.append("<div style='color: #34d399; font-weight: bold;'>✓ Nenhuma pendência ou advertência impeditiva detectada. Instalação em conformidade técnica.</div>")

        self.txt_warnings.setHtml("".join(html_blocks))

    def _on_action_generate_pdf(self) -> None:
        """Gera e emite a Memória de Cálculo em PDF."""
        lic = self.license_manager.get_license()
        if not lic.is_pdf_allowed:
            QMessageBox.warning(
                self,
                "Recurso Bloqueado no Plano Free",
                "A emissão de Memória de Cálculo em PDF está bloqueada no Plano Free.<br/><br/>"
                "Para emitir memórias de cálculo técnicas completas, ative o Plano modo local de revisão."
            )
            return

        self._sync_ui_to_project()
        if not self.current_project.calculation_result:
            msg_calc = QMessageBox(self)
            msg_calc.setWindowTitle("Cálculo Pendente")
            msg_calc.setIcon(QMessageBox.Icon.Question)
            msg_calc.setText("O projeto ainda não foi calculado.<br/><br/>Deseja executar o cálculo agora antes de emitir a Memória de Cálculo?")
            btn_sim = msg_calc.addButton("Sim", QMessageBox.ButtonRole.YesRole)
            btn_nao = msg_calc.addButton("Não", QMessageBox.ButtonRole.NoRole)
            msg_calc.setDefaultButton(btn_sim)
            msg_calc.exec()
            if msg_calc.clickedButton() == btn_sim:
                self._on_action_calculate()
            else:
                return

        default_filename = f"Memoria_Calculo_{self.current_project.title.replace(' ', '_')}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Memória de Cálculo em PDF",
            default_filename,
            "Documentos PDF (*.pdf);;Todos os Arquivos (*)",
        )

        if filepath:
            try:
                out_pdf = self.report_generator.generate_pdf(self.current_project, filepath, license_data=lic)
                self.statusBar().showMessage(f"Memória de Cálculo gerada com sucesso: {os.path.basename(out_pdf)}", 5000)

                msg_open = QMessageBox(self)
                msg_open.setWindowTitle("PDF Gerado com Sucesso")
                msg_open.setIcon(QMessageBox.Icon.Information)
                msg_open.setText(
                    "<b>A Memória de Cálculo foi salva com sucesso!</b><br/><br/>"
                    f"<b>Arquivo:</b><br/>{out_pdf}<br/><br/>"
                    "Deseja abrir o arquivo agora para visualização?"
                )
                btn_sim = msg_open.addButton("Sim", QMessageBox.ButtonRole.YesRole)
                btn_nao = msg_open.addButton("Não", QMessageBox.ButtonRole.NoRole)
                msg_open.setDefaultButton(btn_sim)
                msg_open.exec()

                if msg_open.clickedButton() == btn_sim:
                    os.startfile(out_pdf)
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Gerar PDF", f"Falha ao compilar o relatório PDF:\n{str(e)}")

    def _refresh_bom_tab(self) -> None:
        """Atualiza a aba de Lista de Materiais (BOM) com base no estado do projeto."""
        project = self.current_project
        lic = self.license_manager.get_license()
        if not lic.is_bom_allowed:
            self.lbl_bom_status.setText("🔒 Lista de Materiais (BOM) disponível no modo local de revisão")
            self.lbl_bom_status.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 13px;")
            self.btn_export_bom_excel.setEnabled(False)
            self._update_kpi_value(self.card_bom_cable, "-")
            self._update_kpi_value(self.card_bom_posts, "-")
            self._update_kpi_value(self.card_bom_items, "-")
            self._update_kpi_value(self.card_bom_fix, "-")
            self.table_bom.setRowCount(0)
            return

        if not project.can_generate_bom:
            if project.status == ProjectStatus.CALCULATED_REJECTED:
                self.lbl_bom_status.setText("❌ BLOQUEADO — Projeto com Dimensionamento Reprovado")
                self.lbl_bom_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 13px;")
            elif project.status == ProjectStatus.INVALIDATED:
                self.lbl_bom_status.setText("⚠️ BLOQUEADO — Dados Alterados (Recálculo Necessário)")
                self.lbl_bom_status.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 13px;")
            elif project.calculation_result is None:
                self.lbl_bom_status.setText("🔒 BLOQUEADO — Exige Execução do Cálculo Estrutural (F5)")
                self.lbl_bom_status.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 13px;")
            else:
                self.lbl_bom_status.setText("🔒 BLOQUEADO — Pendências de ART ou Validação da Estrutura")
                self.lbl_bom_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 13px;")

            self.btn_export_bom_excel.setEnabled(False)
            self._update_kpi_value(self.card_bom_cable, "-")
            self._update_kpi_value(self.card_bom_posts, "-")
            self._update_kpi_value(self.card_bom_items, "-")
            self._update_kpi_value(self.card_bom_fix, "-")
            self.table_bom.setRowCount(0)
            return

        try:
            bom = project.generate_bom(license_data=lic)
            self.lbl_bom_status.setText("✓ LIBERADO — Quantitativo Normatizado Conforme NR-35 / NBR 16325-2")
            self.lbl_bom_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
            self.btn_export_bom_excel.setEnabled(True)

            self._update_kpi_value(self.card_bom_cable, f"{bom.cable_total_length_m:.1f} m")
            self._update_kpi_value(self.card_bom_posts, f"{bom.total_posts_count} un")
            self._update_kpi_value(self.card_bom_items, f"{bom.total_items_count} tipos")
            self._update_kpi_value(self.card_bom_fix, project.installation.category.value)

            self.table_bom.setRowCount(len(bom.items))
            for i, it in enumerate(bom.items):
                # 0: Item
                item_num = QTableWidgetItem(str(i + 1))
                item_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_bom.setItem(i, 0, item_num)

                # 1: Código
                item_code = QTableWidgetItem(it.item_code)
                item_code.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_code.setForeground(QColor("#38bdf8"))
                self.table_bom.setItem(i, 1, item_code)

                # 2: Categoria
                item_cat = QTableWidgetItem(it.category)
                self.table_bom.setItem(i, 2, item_cat)

                # 3: Componente
                item_name = QTableWidgetItem(it.name)
                item_name.setForeground(QColor("#f8fafc"))
                self.table_bom.setItem(i, 3, item_name)

                # 4: Especificação Técnica
                item_spec = QTableWidgetItem(it.specification)
                self.table_bom.setItem(i, 4, item_spec)

                # 5: Qtd.
                qtd_str = f"{it.quantity:,.1f}" if (it.quantity % 1 != 0) else f"{int(it.quantity)}"
                item_qtd = QTableWidgetItem(qtd_str)
                item_qtd.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_qtd.setForeground(QColor("#10b981"))
                self.table_bom.setItem(i, 5, item_qtd)

                # 6: Un.
                item_un = QTableWidgetItem(it.unit)
                item_un.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_bom.setItem(i, 6, item_un)

                # 7: Instruções de Montagem
                item_notes = QTableWidgetItem(it.technical_notes)
                item_notes.setForeground(QColor("#94a3b8"))
                self.table_bom.setItem(i, 7, item_notes)

        except Exception as e:
            self.lbl_bom_status.setText(f"⚠️ Erro ao calcular BOM: {str(e)}")
            self.lbl_bom_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 13px;")
            self.btn_export_bom_excel.setEnabled(False)

    def _on_action_export_bom_excel(self) -> None:
        """Exporta a Lista de Materiais (BOM) para uma planilha Excel (.xlsx)."""
        lic = self.license_manager.get_license()
        if not lic.is_bom_allowed or not lic.is_bom_export_allowed:
            QMessageBox.warning(
                self,
                "Recurso Bloqueado no Plano Free",
                "A exportação da Lista de Materiais (BOM) para Excel está bloqueada no Plano Free.<br/><br/>"
                "Para exportar a Lista de Materiais e quantitativos, ative o Plano modo local de revisão."
            )
            return

        self._sync_ui_to_project()
        if not self.current_project.can_generate_bom:
            msg_warn = QMessageBox(self)
            msg_warn.setWindowTitle("Exportação Bloqueada")
            msg_warn.setIcon(QMessageBox.Icon.Warning)
            msg_warn.setText(
                "<b>A Lista de Materiais não pode ser exportada no momento.</b><br/><br/>"
                "Para liberar a lista de materiais, certifique-se de que:<br/>"
                "• A linha de vida foi calculada com sucesso (F5);<br/>"
                "• Todos os critérios de segurança (FS &ge; 2.0 e ZLQ) foram aprovados;<br/>"
                "• Não há pendências estruturais impeditivas (ex: validação da fixação / ART)."
            )
            msg_warn.exec()
            return

        default_filename = f"BOM_{self.current_project.title.replace(' ', '_')}.xlsx"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Lista de Materiais em Excel",
            default_filename,
            "Planilhas Excel (*.xlsx);;Todos os Arquivos (*)",
        )

        if filepath:
            try:
                bom = self.current_project.generate_bom(license_data=lic)
                out_excel = BOMGenerator.export_to_excel(bom, filepath, license_data=lic)
                self.statusBar().showMessage(f"Lista de Materiais salva com sucesso: {os.path.basename(out_excel)}", 5000)

                msg_open = QMessageBox(self)
                msg_open.setWindowTitle("Planilha Excel Gerada")
                msg_open.setIcon(QMessageBox.Icon.Information)
                msg_open.setText(
                    "<b>A Lista de Materiais (BOM) foi exportada com sucesso!</b><br/><br/>"
                    f"<b>Arquivo:</b><br/>{out_excel}<br/><br/>"
                    "Deseja abrir o arquivo agora no Excel?"
                )
                btn_sim = msg_open.addButton("Sim", QMessageBox.ButtonRole.YesRole)
                btn_nao = msg_open.addButton("Não", QMessageBox.ButtonRole.NoRole)
                msg_open.setDefaultButton(btn_sim)
                msg_open.exec()

                if msg_open.clickedButton() == btn_sim:
                    os.startfile(out_excel)
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Exportar Excel", f"Falha ao gerar a planilha de materiais:\n{str(e)}")

    def _on_action_print(self) -> None:
        """Ação de impressão direta do relatório técnico."""
        lic = self.license_manager.get_license()
        if not lic.is_print_allowed:
            QMessageBox.warning(
                self,
                "Impressão Bloqueada no Plano Free",
                "A impressão direta de relatórios técnicos está bloqueada no Plano Free.<br/><br/>"
                "Para imprimir relatórios, ative uma licença modo local de revisão."
            )
            return

        self._sync_ui_to_project()
        try:
            def choose_printer_and_submit(pdf_path: str) -> bool:
                printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                printer.setDocName(f"LineLife - {self.current_project.title}")
                print_dialog = QPrintDialog(printer, self)
                print_dialog.setWindowTitle("Imprimir Relatório Técnico")
                print_dialog.setOption(QPrintDialog.PrintDialogOption.PrintPageRange, True)
                print_dialog.setOption(QPrintDialog.PrintDialogOption.PrintCurrentPage, False)
                print_dialog.setOption(QPrintDialog.PrintDialogOption.PrintSelection, False)
                print_dialog.setMinMax(1, get_pdf_page_count(pdf_path))
                if print_dialog.exec() != QDialog.DialogCode.Accepted:
                    return False
                print_pdf_document(pdf_path, printer)
                return True

            submitted = self.service.print_report(self.current_project, choose_printer_and_submit)
            if submitted is False:
                return
            QMessageBox.information(
                self,
                "Impressão",
                "Relatório enviado com sucesso à impressora selecionada."
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro de Impressão", f"Falha ao imprimir relatório:\n{str(e)}")

    def _on_action_new(self) -> None:
        if self.current_project.is_dirty:
            msg_new = QMessageBox(self)
            msg_new.setWindowTitle("Alterações Não Salvas")
            msg_new.setIcon(QMessageBox.Icon.Warning)
            msg_new.setText("Existem alterações não salvas no projeto atual.<br/><br/>Deseja descartar as alterações e criar um novo projeto?")
            btn_sim = msg_new.addButton("Sim", QMessageBox.ButtonRole.YesRole)
            btn_nao = msg_new.addButton("Não", QMessageBox.ButtonRole.NoRole)
            msg_new.setDefaultButton(btn_nao)
            msg_new.exec()
            if msg_new.clickedButton() != btn_sim:
                return
        self.current_project = self.service.create_project()
        self.current_file_path = None
        self.load_project_to_ui(self.current_project)
        self.statusBar().showMessage("Novo projeto iniciado.", 3000)

    def _on_action_open(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(self, "Abrir Projeto de Linha de Vida", "", "Projeto Linha de Vida (*.lvd);;Todos os Arquivos (*)")
        if filepath:
            try:
                project = self.service.load_project(filepath)
                self.current_file_path = filepath
                self.load_project_to_ui(project)
                if project.is_read_only:
                    self.statusBar().showMessage(f"Projeto aberto em MODO SOMENTE LEITURA: {os.path.basename(filepath)}", 6000)
                    QMessageBox.information(
                        self,
                        "Modo Somente Leitura",
                        "Este projeto possui múltiplos vãos e foi aberto sob o Plano Free.<br/><br/>"
                        "O arquivo foi preservado intacto em <b>modo somente leitura</b>. "
                        "A edição, o recálculo e o salvamento estão bloqueados para respeitar o limite do plano Free.<br/><br/>"
                        "Para editar projetos de até 30 vãos, ative uma licença modo local de revisão."
                    )
                else:
                    self.statusBar().showMessage(f"Projeto aberto: {os.path.basename(filepath)}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Abrir", f"Falha ao carregar o projeto: {str(e)}")

    def _on_action_save(self) -> None:
        if self.current_project.is_read_only:
            QMessageBox.warning(
                self,
                "Salvamento Bloqueado",
                "Projetos abertos em modo somente leitura (múltiplos vãos sob licença Free) não podem ser salvos.<br/><br/>"
                "Seus dados originais permanecem 100% preservados em disco."
            )
            return
        self._sync_ui_to_project()
        if not self.current_file_path:
            self._on_action_save_as()
            return
        try:
            self.service.save_project(self.current_project, self.current_file_path)
            self.statusBar().showMessage(f"Projeto salvo com sucesso: {os.path.basename(self.current_file_path)}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Salvar", f"Falha ao salvar o projeto: {str(e)}")

    def _on_action_save_as(self) -> None:
        if self.current_project.is_read_only:
            QMessageBox.warning(
                self,
                "Salvamento Bloqueado",
                "Projetos abertos em modo somente leitura (múltiplos vãos sob licença Free) não podem ser salvos.<br/><br/>"
                "Seus dados originais permanecem 100% preservados em disco."
            )
            return
        self._sync_ui_to_project()
        filepath, _ = QFileDialog.getSaveFileName(self, "Salvar Projeto Como", f"{self.current_project.title}.lvd", "Projeto Linha de Vida (*.lvd)")
        if filepath:
            try:
                self.service.save_project(self.current_project, filepath)
                self.current_file_path = filepath
                self.statusBar().showMessage(f"Projeto salvo em: {os.path.basename(filepath)}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Salvar", f"Falha ao salvar o projeto: {str(e)}")

    def _on_action_clone(self) -> None:
        if self.current_project.is_read_only:
            QMessageBox.warning(
                self,
                "Clonagem Bloqueada",
                "Projetos abertos em modo somente leitura (múltiplos vãos sob licença Free) não podem ser duplicados ou clonados.<br/><br/>"
                "Para criar novos projetos com múltiplos vãos, ative uma licença modo local de revisão."
            )
            return
        cloned = self.service.clone_project(self.current_project)
        self.current_file_path = None
        self.load_project_to_ui(cloned)
        QMessageBox.information(self, "Projeto Duplicado", f"O projeto foi duplicado com sucesso com o título '{cloned.title}'.")

    def _update_license_ui(self) -> None:
        """Atualiza o indicador local do snapshot público."""
        self.btn_license_badge.setText("LOCAL REVIEW")
        self.btn_license_badge.setStyleSheet(
            "QPushButton { background-color: #475569; color: #ffffff; padding: 4px 10px; "
            "border-radius: 4px; font-weight: bold; font-size: 11px; border: none; }"
        )
        self.btn_license_badge.setToolTip("Modo local para revisão do código.")

    def _on_action_about(self) -> None:
        """Exibe informações neutras do snapshot público."""
        msg = QMessageBox(self)
        msg.setWindowTitle("Sobre o LineLife")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(
            "<b>LineLife — Public Review</b><br/><br/>"
            "Snapshot local para inspeção técnica e validação de cálculos.<br/>"
            "Este modo não usa serviços externos nem dados operacionais."
        )
        msg.exec()
