"""Formulários dinâmicos e condicionais para cada tipo de instalação física."""

from typing import Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from src.domain.installation_types import (
    IndustrialInstallation,
    InstallationBase,
    InstallationCategory,
    MunckInstallation,
    RoofInstallation,
    SlabInstallation,
)


class SlabFormWidget(QWidget):
    """Subformulário para Laje de concreto."""
    changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QFormLayout(self)

        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Concreto Armado Maciço", "Laje Nervurada", "Laje Protendida"])
        self.cmb_type.currentIndexChanged.connect(self._on_change)

        self.spn_thickness = QDoubleSpinBox()
        self.spn_thickness.setRange(50.0, 1000.0)
        self.spn_thickness.setValue(150.0)
        self.spn_thickness.setSuffix(" mm")
        self.spn_thickness.valueChanged.connect(self._on_change)

        self.spn_fck = QDoubleSpinBox()
        self.spn_fck.setRange(15.0, 100.0)
        self.spn_fck.setValue(25.0)
        self.spn_fck.setSuffix(" MPa")
        self.spn_fck.valueChanged.connect(self._on_change)

        self.cmb_anchor = QComboBox()
        self.cmb_anchor.addItems(["Chumbador Químico Injeção", "Chumbador Mecânico Expansão", "Barra Transpassante"])
        self.cmb_anchor.currentIndexChanged.connect(self._on_change)

        self.spn_edge_dist = QDoubleSpinBox()
        self.spn_edge_dist.setRange(50.0, 2000.0)
        self.spn_edge_dist.setValue(200.0)
        self.spn_edge_dist.setSuffix(" mm")
        self.spn_edge_dist.valueChanged.connect(self._on_change)

        self.chk_validated = QCheckBox("Estrutura da laje validada por Engenheiro Civil")
        self.chk_validated.setChecked(True)
        self.chk_validated.toggled.connect(self._on_change)

        self.txt_art = QLineEdit("ART-2026-LAJE-01")
        self.txt_art.textChanged.connect(self._on_change)

        layout.addRow("Tipo de Laje:", self.cmb_type)
        layout.addRow("Espessura da Laje:", self.spn_thickness)
        layout.addRow("Resistência do Concreto (fck):", self.spn_fck)
        layout.addRow("Tipo de Fixação / Ancoragem:", self.cmb_anchor)
        layout.addRow("Distância da Borda Livre:", self.spn_edge_dist)
        layout.addRow("", self.chk_validated)
        layout.addRow("Anotação de Resp. Técnica (ART):", self.txt_art)

    def _on_change(self, *args) -> None:
        self.changed.emit()

    def get_data(self) -> SlabInstallation:
        return SlabInstallation(
            slab_type=self.cmb_type.currentText(),
            thickness_mm=self.spn_thickness.value(),
            concrete_fck_mpa=self.spn_fck.value(),
            anchor_type=self.cmb_anchor.currentText(),
            anchor_edge_distance_mm=self.spn_edge_dist.value(),
            is_structure_validated_by_engineer=self.chk_validated.isChecked(),
            responsible_engineer_art=self.txt_art.text().strip(),
        )

    def set_data(self, inst: SlabInstallation) -> None:
        idx = self.cmb_type.findText(inst.slab_type)
        if idx >= 0:
            self.cmb_type.setCurrentIndex(idx)
        if inst.thickness_mm:
            self.spn_thickness.setValue(inst.thickness_mm)
        if inst.concrete_fck_mpa:
            self.spn_fck.setValue(inst.concrete_fck_mpa)
        idx_anc = self.cmb_anchor.findText(inst.anchor_type)
        if idx_anc >= 0:
            self.cmb_anchor.setCurrentIndex(idx_anc)
        if inst.anchor_edge_distance_mm:
            self.spn_edge_dist.setValue(inst.anchor_edge_distance_mm)
        self.chk_validated.setChecked(inst.is_structure_validated_by_engineer)
        self.txt_art.setText(inst.responsible_engineer_art or "")


class RoofFormWidget(QWidget):
    """Subformulário para Telhado."""
    changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QFormLayout(self)

        self.cmb_roof_type = QComboBox()
        self.cmb_roof_type.addItems(["Duas Águas", "Shed", "Arco", "Plano"])
        self.cmb_roof_type.currentIndexChanged.connect(self._on_change)

        self.cmb_tile = QComboBox()
        self.cmb_tile.addItems([
            "Metálica Trapezoidal",
            "Metálica Zipada",
            "Termoacústica (Sanduíche)",
            "Fibrocimento Ondulada (Bloqueante)"
        ])
        self.cmb_tile.currentIndexChanged.connect(self._on_change)

        self.cmb_support = QComboBox()
        self.cmb_support.addItems(["Terça Metálica Z / C", "Tesoura Estrutural", "Viga de Concreto"])
        self.cmb_support.currentIndexChanged.connect(self._on_change)

        self.spn_spacing = QDoubleSpinBox()
        self.spn_spacing.setRange(500.0, 5000.0)
        self.spn_spacing.setValue(1500.0)
        self.spn_spacing.setSuffix(" mm")
        self.spn_spacing.valueChanged.connect(self._on_change)

        self.spn_slope = QDoubleSpinBox()
        self.spn_slope.setRange(0.0, 100.0)
        self.spn_slope.setValue(10.0)
        self.spn_slope.setSuffix(" %")
        self.spn_slope.valueChanged.connect(self._on_change)

        self.chk_validated = QCheckBox("Estrutura de suporte validada por Engenheiro")
        self.chk_validated.setChecked(True)
        self.chk_validated.toggled.connect(self._on_change)

        self.txt_art = QLineEdit("ART-2026-TELHADO-01")
        self.txt_art.textChanged.connect(self._on_change)

        layout.addRow("Tipo de Cobertura:", self.cmb_roof_type)
        layout.addRow("Tipo de Telha:", self.cmb_tile)
        layout.addRow("Estrutura Portante (Terças):", self.cmb_support)
        layout.addRow("Espaçamento das Terças:", self.spn_spacing)
        layout.addRow("Inclinação do Telhado:", self.spn_slope)
        layout.addRow("", self.chk_validated)
        layout.addRow("ART do Responsável:", self.txt_art)

    def _on_change(self, *args) -> None:
        self.changed.emit()

    def get_data(self) -> RoofInstallation:
        return RoofInstallation(
            roof_type=self.cmb_roof_type.currentText(),
            tile_type=self.cmb_tile.currentText(),
            support_element=self.cmb_support.currentText(),
            support_spacing_mm=self.spn_spacing.value(),
            roof_slope_percent=self.spn_slope.value(),
            is_structure_validated_by_engineer=self.chk_validated.isChecked(),
            responsible_engineer_art=self.txt_art.text().strip(),
        )

    def set_data(self, inst: RoofInstallation) -> None:
        idx = self.cmb_tile.findText(inst.tile_type)
        if idx >= 0:
            self.cmb_tile.setCurrentIndex(idx)
        if inst.support_spacing_mm:
            self.spn_spacing.setValue(inst.support_spacing_mm)
        self.spn_slope.setValue(inst.roof_slope_percent)
        self.chk_validated.setChecked(inst.is_structure_validated_by_engineer)
        self.txt_art.setText(inst.responsible_engineer_art or "")


class IndustrialFormWidget(QWidget):
    """Subformulário para Área Industrial."""
    changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QFormLayout(self)

        self.cmb_struct = QComboBox()
        self.cmb_struct.addItems(["Perfil I / H Laminado (Viga Metálica)", "Perfil Tubular Quadrado/Redondo", "Treliça Metálica"])
        self.cmb_struct.currentIndexChanged.connect(self._on_change)

        self.cmb_steel = QComboBox()
        self.cmb_steel.addItems(["ASTM A36", "ASTM A572 Grau 50", "Inox 316L (Ambiente Corrosivo)"])
        self.cmb_steel.currentIndexChanged.connect(self._on_change)

        self.cmb_attach = QComboBox()
        self.cmb_attach.addItems(["Abraçadeira Tipo Grampo (Clamp)", "Bocal Flangeado Parafusado", "Solda Estrutural Homologada"])
        self.cmb_attach.currentIndexChanged.connect(self._on_change)

        self.spn_height = QDoubleSpinBox()
        self.spn_height.setRange(1.0, 100.0)
        self.spn_height.setValue(6.0)
        self.spn_height.setSuffix(" m")
        self.spn_height.valueChanged.connect(self._on_change)

        self.chk_validated = QCheckBox("Estrutura metálica existente verificada e apta para cargas dinâmicas")
        self.chk_validated.setChecked(True)
        self.chk_validated.toggled.connect(self._on_change)

        self.txt_art = QLineEdit("ART-2026-IND-01")
        self.txt_art.textChanged.connect(self._on_change)

        layout.addRow("Perfil Estrutural:", self.cmb_struct)
        layout.addRow("Classe do Aço:", self.cmb_steel)
        layout.addRow("Fixação dos Postes:", self.cmb_attach)
        layout.addRow("Altura de Trabalho:", self.spn_height)
        layout.addRow("", self.chk_validated)
        layout.addRow("ART do Responsável:", self.txt_art)

    def _on_change(self, *args) -> None:
        self.changed.emit()

    def get_data(self) -> IndustrialInstallation:
        return IndustrialInstallation(
            structure_type=self.cmb_struct.currentText(),
            steel_grade=self.cmb_steel.currentText(),
            post_attachment_method=self.cmb_attach.currentText(),
            working_height_m=self.spn_height.value(),
            is_structure_validated_by_engineer=self.chk_validated.isChecked(),
            responsible_engineer_art=self.txt_art.text().strip(),
        )

    def set_data(self, inst: IndustrialInstallation) -> None:
        idx = self.cmb_struct.findText(inst.structure_type)
        if idx >= 0:
            self.cmb_struct.setCurrentIndex(idx)
        self.spn_height.setValue(inst.working_height_m)
        self.chk_validated.setChecked(inst.is_structure_validated_by_engineer)
        self.txt_art.setText(inst.responsible_engineer_art or "")


class MunckFormWidget(QWidget):
    """Subformulário para Caminhão Munck."""
    changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QFormLayout(self)

        self.txt_model = QLineEdit("Caminhão Munck Traçado 6x4")
        self.txt_model.textChanged.connect(self._on_change)

        self.cmb_region = QComboBox()
        self.cmb_region.addItems(["Sobre a Carroceria de Carga", "Longarinas do Chassi", "Suporte Integrado nas Patolas"])
        self.cmb_region.currentIndexChanged.connect(self._on_change)

        self.spn_boom_h = QDoubleSpinBox()
        self.spn_boom_h.setRange(2.0, 50.0)
        self.spn_boom_h.setValue(12.0)
        self.spn_boom_h.setSuffix(" m")
        self.spn_boom_h.valueChanged.connect(self._on_change)

        self.lbl_warning = QLabel(
            "⚠️ ATENÇÃO: É proibido assumir capacidade do chassi sem validação de Engenheiro Mecânico com ART."
        )
        self.lbl_warning.setStyleSheet("color: #f59e0b; font-weight: bold;")
        self.lbl_warning.setWordWrap(True)

        self.chk_motion = QCheckBox("Veículo opera em movimento (TERMINANTEMENTE PROIBIDO)")
        self.chk_motion.setChecked(False)
        self.chk_motion.toggled.connect(self._on_change)

        self.chk_validated = QCheckBox("Reforço estrutural validado por Engenheiro Mecânico com ART")
        self.chk_validated.setChecked(True)
        self.chk_validated.toggled.connect(self._on_change)

        self.txt_art = QLineEdit("ART-2026-MEC-MUNCK")
        self.txt_art.textChanged.connect(self._on_change)

        layout.addRow("Modelo do Veículo:", self.txt_model)
        layout.addRow("Região de Ancoragem:", self.cmb_region)
        layout.addRow("Altura da Lança:", self.spn_boom_h)
        layout.addRow("", self.lbl_warning)
        layout.addRow("", self.chk_motion)
        layout.addRow("", self.chk_validated)
        layout.addRow("ART do Eng. Mecânico:", self.txt_art)

    def _on_change(self, *args) -> None:
        self.changed.emit()

    def get_data(self) -> MunckInstallation:
        return MunckInstallation(
            vehicle_model=self.txt_model.text().strip(),
            chassis_region=self.cmb_region.currentText(),
            max_boom_height_m=self.spn_boom_h.value(),
            allows_vehicle_motion=self.chk_motion.isChecked(),
            is_structure_validated_by_engineer=self.chk_validated.isChecked(),
            responsible_engineer_art=self.txt_art.text().strip(),
        )

    def set_data(self, inst: MunckInstallation) -> None:
        self.txt_model.setText(inst.vehicle_model)
        self.spn_boom_h.setValue(inst.max_boom_height_m)
        self.chk_motion.setChecked(inst.allows_vehicle_motion)
        self.chk_validated.setChecked(inst.is_structure_validated_by_engineer)
        self.txt_art.setText(inst.responsible_engineer_art or "")


class InstallationContainerWidget(QWidget):
    """Container seletor com alternância dinâmica dos formulários especializados."""
    changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        h_sel = QHBoxLayout()
        lbl = QLabel("Tipo de Aplicação / Instalação:")
        lbl.setStyleSheet("font-weight: bold; color: #38bdf8;")
        self.cmb_category = QComboBox()
        self.cmb_category.addItem("Área Industrial / Estrutura Metálica", InstallationCategory.INDUSTRIAL.value)
        self.cmb_category.addItem("Laje de Concreto Armado", InstallationCategory.SLAB.value)
        self.cmb_category.addItem("Telhado / Cobertura", InstallationCategory.ROOF.value)
        self.cmb_category.addItem("Caminhão Munck / Veículo", InstallationCategory.MUNCK.value)
        self.cmb_category.currentIndexChanged.connect(self._on_category_changed)

        h_sel.addWidget(lbl)
        h_sel.addWidget(self.cmb_category)
        h_sel.addStretch()
        layout.addLayout(h_sel)

        self.stack = QStackedWidget()
        self.form_ind = IndustrialFormWidget()
        self.form_slab = SlabFormWidget()
        self.form_roof = RoofFormWidget()
        self.form_munck = MunckFormWidget()

        self.form_ind.changed.connect(self._on_child_changed)
        self.form_slab.changed.connect(self._on_child_changed)
        self.form_roof.changed.connect(self._on_child_changed)
        self.form_munck.changed.connect(self._on_child_changed)

        self.stack.addWidget(self.form_ind)   # 0
        self.stack.addWidget(self.form_slab)  # 1
        self.stack.addWidget(self.form_roof)  # 2
        self.stack.addWidget(self.form_munck) # 3

        grp = QGroupBox("Parâmetros Estruturais Específicos da Instalação")
        grp_layout = QVBoxLayout(grp)
        grp_layout.addWidget(self.stack)
        layout.addWidget(grp)

    def _on_category_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.changed.emit()

    def _on_child_changed(self) -> None:
        self.changed.emit()

    def get_installation(self) -> InstallationBase:
        idx = self.stack.currentIndex()
        if idx == 1:
            return self.form_slab.get_data()
        elif idx == 2:
            return self.form_roof.get_data()
        elif idx == 3:
            return self.form_munck.get_data()
        else:
            return self.form_ind.get_data()

    def set_installation(self, inst: InstallationBase) -> None:
        if isinstance(inst, SlabInstallation):
            self.cmb_category.setCurrentIndex(1)
            self.form_slab.set_data(inst)
        elif isinstance(inst, RoofInstallation):
            self.cmb_category.setCurrentIndex(2)
            self.form_roof.set_data(inst)
        elif isinstance(inst, MunckInstallation):
            self.cmb_category.setCurrentIndex(3)
            self.form_munck.set_data(inst)
        else:
            self.cmb_category.setCurrentIndex(0)
            if isinstance(inst, IndustrialInstallation):
                self.form_ind.set_data(inst)
