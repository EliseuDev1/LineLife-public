"""Motor de Regras Técnicas para Lista de Materiais Inteligente (Bill of Materials - BOM).

Gera o quantitativo normatizado de componentes físicos da linha de vida conforme
as diretrizes da NR-35 (Anexo II), ABNT NBR 16325-1, ABNT NBR 16325-2 e ABNT NBR ISO 2408.
"""

import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    openpyxl = None
    HAS_OPENPYXL = False

from src.domain.installation_types import InstallationCategory
from src.domain.project import Project, ProjectStatus


@dataclass(frozen=True)
class BOMItem:
    """Item individual da Lista de Materiais (Bill of Materials)."""
    item_code: str
    category: str
    name: str
    specification: str
    quantity: float
    unit: str
    technical_notes: str


@dataclass
class BillOfMaterials:
    """Lista de Materiais consolidada com rastreabilidade técnica."""
    project_title: str
    project_id: str
    client: str
    responsible_engineer: str
    items: List[BOMItem] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_spans_length_m: float = 0.0
    cable_total_length_m: float = 0.0
    total_posts_count: int = 0

    @property
    def total_items_count(self) -> int:
        """Quantidade total de itens cadastrados na lista."""
        return len(self.items)


class BOMGenerator:
    """Motor de quantificação e especificações técnicas de materiais."""

    @classmethod
    def generate(cls, project: Project, license_data: Optional[Any] = None) -> BillOfMaterials:
        """Gera a Lista de Materiais (BOM) completa e detalhada para o projeto.
        
        Exige que o projeto esteja calculado, estruturalmente aprovado e sem pendências.
        """
        if license_data is not None:
            license_data.assert_can_access_bom()

        if not project.can_generate_bom:
            raise ValueError(
                "A Lista de Materiais (BOM) só pode ser gerada para projetos com cálculo "
                "estrutural concluído, formalmente aprovado e sem pendências de ART/infraestrutura."
            )

        items: List[BOMItem] = []
        spans = project.spans
        num_spans = len(spans)
        num_posts = num_spans + 1
        num_intermediate_posts = max(0, num_posts - 2)

        total_span_m = sum(s.span_mm for s in spans) / 1000.0
        cabo = project.cable
        res = project.calculation_result
        inst = project.installation

        # ---------------------------------------------------------------------
        # 1. CABO DE AÇO
        # ---------------------------------------------------------------------
        # Sobra técnica para confecção de laçadas, sapatilhos e curso de esticadores:
        # 2,0 m por ancoragem de extremidade = + 4,0 m no total.
        sobra_montagem_m = 4.0
        comprimento_cabo_total = math.ceil((total_span_m + sobra_montagem_m) * 2.0) / 2.0 # Múltiplo de 0,5 m

        cabo_spec = cabo.specification if cabo else "Cabo de aço conforme NBR ISO 2408"
        cabo_diam = f"Ø {cabo.diameter_mm:.1f} mm" if cabo else "Conforme projeto"
        cabo_fu = f"{cabo.min_breaking_load_kgf:,.0f} kgf" if cabo else "-"

        items.append(
            BOMItem(
                item_code="CAB-001",
                category="Linha Principal",
                name="Cabo de Aço para Linha de Vida",
                specification=f"{cabo_spec} — {cabo_diam} (Carga Mín. Ruptura Fu = {cabo_fu})",
                quantity=comprimento_cabo_total,
                unit="m",
                technical_notes=(
                    f"Comprimento total dos vãos ({total_span_m:.1f} m) acrescido de "
                    f"{sobra_montagem_m:.1f} m para sapatilhos, laçadas e curso de esticador."
                ),
            )
        )

        # ---------------------------------------------------------------------
        # 2. POSTES DE EXTREMIDADE (ANCORAGENS TERMINAIS)
        # ---------------------------------------------------------------------
        # As ancoragens finais absorvem a tração longitudinal total T
        t_ext_kgf = res.end_anchor_load_kgf if res else 2000.0
        t_ext_kn = (t_ext_kgf * 9.80665) / 1000.0
        capacidade_min_poste_kgf = max(3000.0, t_ext_kgf * 1.5)

        items.append(
            BOMItem(
                item_code="PST-EXT-01",
                category="Estrutura e Postes",
                name="Poste de Ancoragem de Extremidade",
                specification=(
                    f"Poste terminal reforçado para tração longitudinal de no mínimo "
                    f"{capacidade_min_poste_kgf:,.0f} kgf ({capacidade_min_poste_kgf*9.80665/1000.0:.1f} kN). "
                    f"Aço estrutural ASTM A36 / AISI 304 com placa de base furada para 4 fixadores."
                ),
                quantity=2.0,
                unit="pç",
                technical_notes=(
                    f"Projetado para absorver a tração atuante calculada de {t_ext_kgf:,.0f} kgf ({t_ext_kn:.2f} kN) "
                    f"com margem de segurança estrutural."
                ),
            )
        )

        # ---------------------------------------------------------------------
        # 3. POSTES INTERMEDIÁRIOS (PASSADORES DE CABO)
        # ---------------------------------------------------------------------
        if num_intermediate_posts > 0:
            c_vert_kgf = res.intermediate_post_vertical_load_kgf if res else 0.0
            items.append(
                BOMItem(
                    item_code="PST-INT-01",
                    category="Estrutura e Postes",
                    name="Poste Intermediário com Passador Deslizante",
                    specification=(
                        "Poste intermediário com cabeçote passador curvo/articulado que permite "
                        "o deslizamento contínuo do cabo sem atrito cortante. Aço ASTM A36 galvanizado a fogo / AISI 304."
                    ),
                    quantity=float(num_intermediate_posts),
                    unit="pç",
                    technical_notes=(
                        f"Instalado nos pontos intermediários para dividir os vãos. "
                        f"Capacidade vertical calculada: {c_vert_kgf:,.0f} kgf."
                    ),
                )
            )

        # ---------------------------------------------------------------------
        # 4. ESTICADOR DE CABO (TURNBUCKLE)
        # ---------------------------------------------------------------------
        # Linhas longas (> 30 m) ou com muitos vãos se beneficiam de 2 esticadores
        qtd_esticadores = 2.0 if (total_span_m > 30.0 or num_spans >= 4) else 1.0
        items.append(
            BOMItem(
                item_code="EST-001",
                category="Acessórios e Ferragens",
                name="Esticador Pesado para Linha de Vida (Olhal / Manilha)",
                specification=(
                    f"Esticador forjado pesado conforme US Fed. Spec. FF-T-791b ou DIN 1480 reforçado. "
                    f"Corpo em aço forjado galvanizado, rosca com contraporca travante, carga de trabalho compatível com T = {t_ext_kgf:,.0f} kgf."
                ),
                quantity=qtd_esticadores,
                unit="pç",
                technical_notes=(
                    "Utilizado para ajuste fino da flecha inicial de montagem (f1) e retensionamento "
                    "periódico de acomodação do cabo."
                ),
            )
        )

        # ---------------------------------------------------------------------
        # 5. SAPATILHOS DE PROTEÇÃO (THIMBLES)
        # ---------------------------------------------------------------------
        items.append(
            BOMItem(
                item_code="SAP-001",
                category="Acessórios e Ferragens",
                name="Sapatilho de Proteção Reforçado para Cabo de Aço",
                specification=(
                    f"Sapatilho reforçado em aço galvanizado a fogo conforme DIN 6899B / US Fed. Spec., "
                    f"compatível com diâmetro {cabo_diam}."
                ),
                quantity=2.0,
                unit="pç",
                technical_notes="Instalado no interior dos olhais das duas extremidades para evitar esmagamento e desgaste prematuro do cabo.",
            )
        )

        # ---------------------------------------------------------------------
        # 6. GRAMPOS PESADOS DE FIXAÇÃO (CLIPS)
        # ---------------------------------------------------------------------
        diam_mm = cabo.diameter_mm if cabo else 8.0
        if diam_mm <= 8.0:
            grampos_por_ponta = 3
        elif diam_mm <= 12.0:
            grampos_por_ponta = 4
        else:
            grampos_por_ponta = 5

        total_grampos = float(grampos_por_ponta * 2)

        items.append(
            BOMItem(
                item_code="GRP-001",
                category="Acessórios e Ferragens",
                name="Grampos Pesados de Fixação para Cabo (Clipes)",
                specification=(
                    f"Grampo pesado em aço forjado conforme US Fed. Spec. FF-C-450 Type 1 Class 1 "
                    f"(antigo DIN 741 pesado). Compatível com {cabo_diam}."
                ),
                quantity=total_grampos,
                unit="pç",
                technical_notes=(
                    f"Exigência normativa de {grampos_por_ponta} grampos por terminação com espaçamento "
                    f"mínimo de 6 vezes o diâmetro do cabo. A base do grampo deve sempre apoiar no trecho vivo do cabo."
                ),
            )
        )

        # ---------------------------------------------------------------------
        # 7. ABSORVEDOR DE ENERGIA DE LINHA (IN-LINE SHOCK ABSORBER)
        # ---------------------------------------------------------------------
        items.append(
            BOMItem(
                item_code="ABS-001",
                category="Acessórios e Ferragens",
                name="Absorvedor de Energia de Linha (In-line)",
                specification=(
                    "Absorvedor de impacto longitudinal em aço inoxidável AISI 304/316, "
                    "com indicador visual de acionamento/deformação. Carga de ativação calibrada em 6,0 kN (600 kgf)."
                ),
                quantity=1.0,
                unit="pç",
                technical_notes=(
                    "Instalado em série com o cabo na extremidade oposta ao esticador para absorver "
                    "o pico dinâmico da queda e proteger as ancoragens estruturais."
                ),
            )
        )

        # ---------------------------------------------------------------------
        # 8. ELEMENTOS DE FIXAÇÃO À INFRAESTRUTURA (CONFORME TIPO DE INSTALAÇÃO)
        # ---------------------------------------------------------------------
        total_postes = num_posts
        cat = inst.category

        if cat == InstallationCategory.SLAB:
            qtd_chumbadores = float(total_postes * 4)
            items.append(
                BOMItem(
                    item_code="FIX-SLAB-01",
                    category="Fixação Estrutural",
                    name="Chumbador Químico de Alta Performance (Barra Roscada + Resina)",
                    specification=(
                        "Barra roscada M12 em aço zincado/inox classe 5.8 ou 8.8 com porca sextavada e arruela lisa, "
                        "acompanhada de ampola química / resina epóxi bicomponente de alta aderência."
                    ),
                    quantity=qtd_chumbadores,
                    unit="cj",
                    technical_notes=(
                        f"4 fixadores químicos por poste ({total_postes} postes no total). Profundidade de embutimento "
                        f"mínima e torque de aperto conforme memorial de cálculo estrutural da laje."
                    ),
                )
            )

        elif cat == InstallationCategory.INDUSTRIAL:
            qtd_fixadores = float(total_postes * 4)
            items.append(
                BOMItem(
                    item_code="FIX-IND-01",
                    category="Fixação Estrutural",
                    name="Kit de Grampos de Aba Pesados para Viga Metálica (Beam Clamps)",
                    specification=(
                        "Grampo de fixação de abas de vigas I/W em ferro nodular forjado galvanizado, "
                        "com parafuso de aperto temperado e contraporca de segurança."
                    ),
                    quantity=qtd_fixadores,
                    unit="cj",
                    technical_notes=(
                        f"4 grampos de aba por base de poste ({total_postes} postes). "
                        "Permite fixação mecânica direta sem necessidade de solda ou furação das vigas estruturais."
                    ),
                )
            )

        elif cat == InstallationCategory.ROOF:
            items.append(
                BOMItem(
                    item_code="FIX-ROOF-01",
                    category="Fixação Estrutural",
                    name="Kit de Interface Estrutural para Cobertura / Terças",
                    specification=(
                        "Chapa adaptadora para perfil de telha com vedação EPDM integrada e parafusos estruturais "
                        "passantes para amarração direta nas terças metálicas inferiores."
                    ),
                    quantity=float(total_postes),
                    unit="kit",
                    technical_notes=(
                        f"1 kit de interface estrutural por poste ({total_postes} postes). "
                        "Garante estanqueidade contra intempéries e transmissão de esforços para as terças estruturais."
                    ),
                )
            )

        elif cat == InstallationCategory.MUNCK:
            items.append(
                BOMItem(
                    item_code="FIX-MNC-01",
                    category="Fixação Estrutural",
                    name="Kit de Suporte de Ancoragem para Caminhão Munck",
                    specification=(
                        "Mancal articulado de travamento em aço carbono estrutural com pinos de engate rápido "
                        "e travas de retenção tipo R."
                    ),
                    quantity=2.0,
                    unit="kit",
                    technical_notes=(
                        "Fixado nos pontos dedicados da lança e torre do veículo conforme projeto mecânico veicular. "
                        "Uso estritamente proibido com o veículo em movimento."
                    ),
                )
            )

        # ---------------------------------------------------------------------
        # 9. PLACA DE ADVERTÊNCIA E IDENTIFICAÇÃO NORMATIVA (NR-35)
        # ---------------------------------------------------------------------
        users_count = project.user_config.simultaneous_users
        items.append(
            BOMItem(
                item_code="PLC-001",
                category="Sinalização e Segurança",
                name="Placa Metálica de Identificação e Advertência da Linha de Vida (NR-35)",
                specification=(
                    "Placa em alumínio anodizado ou aço inoxidável gravada a laser, resistente a intempéries, "
                    "em conformidade estrita com o Anexo II da NR-35 e NBR 16325-2."
                ),
                quantity=1.0,
                unit="pç",
                technical_notes=(
                    f"Fixada no acesso à linha. Contém: Código {project.project_id}, Carga Máx. Ancoragem ({t_ext_kgf:,.0f} kgf), "
                    f"Capacidade de {users_count} usuário(s) simultâneo(s), Responsável Técnico: {project.responsible_engineer}, "
                    f"ART e Data de Inspeção Anual Obrigatória."
                ),
            )
        )

        return BillOfMaterials(
            project_title=project.title,
            project_id=project.project_id,
            client=project.client,
            responsible_engineer=project.responsible_engineer,
            items=items,
            total_spans_length_m=total_span_m,
            cable_total_length_m=comprimento_cabo_total,
            total_posts_count=num_posts,
        )

    @classmethod
    def export_to_excel(cls, bom: BillOfMaterials, output_filepath: str, license_data: Optional[Any] = None) -> str:
        """Exporta a Lista de Materiais (BOM) para uma planilha Excel (.xlsx) altamente formatada."""
        if license_data is not None:
            license_data.assert_can_export_bom()

        if not HAS_OPENPYXL:
            raise ImportError("A biblioteca 'openpyxl' é necessária para exportação em Excel.")

        if not output_filepath.lower().endswith(".xlsx"):
            output_filepath += ".xlsx"

        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Lista de Materiais - BOM"
        ws.views.sheetView[0].showGridLines = True

        # Estilos corporativos
        color_header_bg = "0284C7" # Azul técnico
        color_title_bg = "0F172A"  # Azul escuro profundo
        color_zebra = "F8FAFC"     # Fundo alternado suave
        color_border = "CBD5E1"

        font_doc_title = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
        font_meta_bold = Font(name="Segoe UI", size=9, bold=True, color="1E293B")
        font_meta_val = Font(name="Segoe UI", size=9, color="334155")
        font_header = Font(name="Segoe UI", size=9, bold=True, color="FFFFFF")
        font_data = Font(name="Segoe UI", size=9, color="0F172A")
        font_data_bold = Font(name="Segoe UI", size=9, bold=True, color="0F172A")
        font_notes = Font(name="Segoe UI", size=8, italic=True, color="475569")

        fill_title = PatternFill(start_color=color_title_bg, end_color=color_title_bg, fill_type="solid")
        fill_header = PatternFill(start_color=color_header_bg, end_color=color_header_bg, fill_type="solid")
        fill_zebra = PatternFill(start_color=color_zebra, end_color=color_zebra, fill_type="solid")
        fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

        thin_side = Side(style="thin", color=color_border)
        cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
        align_right = Alignment(horizontal="right", vertical="center")

        # 1. Título do Documento
        ws.merge_cells("A1:G1")
        cell_title = ws["A1"]
        cell_title.value = "LISTA DE MATERIAIS TÉCNICA (BOM) — LINHA DE VIDA HORIZONTAL FLEXÍVEL"
        cell_title.font = font_doc_title
        cell_title.fill = fill_title
        cell_title.alignment = align_center
        ws.row_dimensions[1].height = 36

        # 2. Metadados do Projeto
        meta = [
            ("Projeto:", bom.project_title, "Código / ID:", bom.project_id),
            ("Cliente:", bom.client, "Data de Emissão:", datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")),
            ("Responsável Técnico:", bom.responsible_engineer, "Extensão Total dos Vãos:", f"{bom.total_spans_length_m:.1f} m"),
            ("Total de Postes:", f"{bom.total_posts_count} postes", "Metragem do Cabo (c/ sobras):", f"{bom.cable_total_length_m:.1f} m"),
        ]

        start_row = 3
        for i, row_data in enumerate(meta):
            r = start_row + i
            ws.cell(row=r, column=1, value=row_data[0]).font = font_meta_bold
            ws.cell(row=r, column=2, value=row_data[1]).font = font_meta_val
            ws.cell(row=r, column=4, value=row_data[2]).font = font_meta_bold
            ws.cell(row=r, column=5, value=row_data[3]).font = font_meta_val
            ws.row_dimensions[r].height = 18

        # 3. Cabeçalho da Tabela de Itens
        headers = ["Item", "Código", "Categoria", "Descrição Técnica do Componente", "Qtd.", "Un.", "Notas Técnicas e Instruções de Montagem"]
        h_row = 8
        ws.row_dimensions[h_row].height = 24

        for col_idx, h_text in enumerate(headers, start=1):
            c = ws.cell(row=h_row, column=col_idx, value=h_text)
            c.font = font_header
            c.fill = fill_header
            c.alignment = align_center
            c.border = cell_border

        # 4. Dados dos Itens
        d_row = h_row + 1
        for idx, it in enumerate(bom.items, start=1):
            ws.row_dimensions[d_row].height = 28
            fill_current = fill_zebra if (idx % 2 == 0) else fill_white

            row_values = [
                (idx, align_center, font_data_bold),
                (it.item_code, align_center, font_data_bold),
                (it.category, align_left, font_data),
                (f"{it.name}\n{it.specification}", align_left, font_data),
                (it.quantity, align_right, font_data_bold),
                (it.unit, align_center, font_data),
                (it.technical_notes, align_left, font_notes),
            ]

            for c_idx, (val, al, fn) in enumerate(row_values, start=1):
                cell = ws.cell(row=d_row, column=c_idx, value=val)
                cell.font = fn
                cell.fill = fill_current
                cell.alignment = al
                cell.border = cell_border

            d_row += 1

        # 5. Ajuste de Larguras de Colunas
        col_widths = {
            1: 8,   # Item
            2: 14,  # Código
            3: 22,  # Categoria
            4: 48,  # Descrição
            5: 10,  # Qtd
            6: 8,   # Un
            7: 52,  # Notas
        }
        for col_idx, width in col_widths.items():
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = width

        wb.save(output_filepath)
        return output_filepath
