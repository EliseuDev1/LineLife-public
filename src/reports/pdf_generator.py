"""Gerador de Memória de Cálculo Estrutural em PDF utilizando ReportLab nativo."""

import math
import os
from datetime import datetime, timezone
from typing import Any, List, Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        HRFlowable,
        Image,
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    HAS_REPORTLAB = True
    BaseCanvas = canvas.Canvas
except ImportError:
    colors = None
    A4 = (595.27, 841.89)
    ParagraphStyle = getSampleStyleSheet = canvas = None
    HRFlowable = Image = KeepTogether = PageBreak = Paragraph = SimpleDocTemplate = Spacer = Table = TableStyle = None
    HAS_REPORTLAB = False
    BaseCanvas = object

from src.core import units
from src.domain.project import Project, ProjectStatus


def resolve_image_path(image_filename: str) -> str:
    """Busca o caminho absoluto da imagem testando locais conhecidos no projeto."""
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "imagens", image_filename)),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "projeto_linha_vida", "imagens", image_filename)),
        os.path.abspath(os.path.join(os.getcwd(), "imagens", image_filename)),
        os.path.abspath(os.path.join(os.getcwd(), "projeto_linha_vida", "imagens", image_filename)),
        os.path.abspath(os.path.join("imagens", image_filename)),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


class NumberedCanvas(BaseCanvas):
    """Canvas com contagem total de páginas, marca d'água de licença e rodapé profissional."""

    watermark_text: Optional[str] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()

        # Marca d'água diagonal semitransparente para modos sem acesso comercial
        wm = getattr(self, "watermark_text", None)
        if wm:
            self.saveState()
            self.setFont("Helvetica-Bold", 32)
            self.setFillColor(colors.HexColor("#94a3b8"), alpha=0.15)
            self.translate(A4[0] / 2, A4[1] / 2)
            self.rotate(45)
            self.drawCentredString(0, 0, str(wm))
            self.restoreState()

        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Linha delimitadora de rodapé
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 28, A4[0] - 36, 28)

        # Informações de cabeçalho e rodapé
        self.drawString(36, 18, "Sistema de Linhas de Vida Horizontais — Memória de Cálculo Conforme NR-35 / NBR 16325-2")
        self.drawRightString(A4[0] - 36, 18, f"Página {self._pageNumber} de {page_count}")
        self.restoreState()


def make_numbered_canvas(watermark: Optional[str] = None):
    """Fábrica de NumberedCanvas com marca d'água configurada."""
    class CustomNumberedCanvas(NumberedCanvas):
        watermark_text = watermark
    return CustomNumberedCanvas


class CalculationReportGenerator:
    """Emissor de Memória de Cálculo Técnica e Rastreável em formato PDF."""

    def __init__(self):
        if HAS_REPORTLAB:
            self.styles = getSampleStyleSheet()
            self._setup_custom_styles()
        else:
            self.styles = None

    def _setup_custom_styles(self) -> None:
        """Define estilos tipográficos para o documento de engenharia."""
        self.title_style = ParagraphStyle(
            "DocTitle",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=colors.HexColor("#0f172a"),
            alignment=1, # Centralizado
        )
        self.subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
            alignment=1,
        )
        self.section_heading = ParagraphStyle(
            "SectionHeading",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#0284c7"),
            spaceBefore=8,
            spaceAfter=3,
            keepWithNext=True,
        )
        self.sub_heading = ParagraphStyle(
            "SubHeading",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0369a1"),
            spaceBefore=5,
            spaceAfter=2,
            keepWithNext=True,
        )
        self.body_style = ParagraphStyle(
            "BodyDark",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
        )
        self.bold_style = ParagraphStyle(
            "BoldDark",
            parent=self.body_style,
            fontName="Helvetica-Bold",
        )
        self.formula_title = ParagraphStyle(
            "FormulaTitle",
            parent=self.body_style,
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.HexColor("#0369a1"),
        )
        self.formula_expr = ParagraphStyle(
            "FormulaExpr",
            parent=self.body_style,
            fontName="Courier-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0f172a"),
        )
        self.step_label = ParagraphStyle(
            "StepLabel",
            parent=self.body_style,
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.HexColor("#0f172a"),
        )
        self.step_math = ParagraphStyle(
            "StepMath",
            parent=self.body_style,
            fontName="Courier",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
        )
        self.step_result = ParagraphStyle(
            "StepResult",
            parent=self.body_style,
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.HexColor("#047857"),
        )
        self.warn_style = ParagraphStyle(
            "WarnText",
            parent=self.body_style,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#b45309"),
        )
        self.danger_style = ParagraphStyle(
            "DangerText",
            parent=self.body_style,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#b91c1c"),
        )
        self.success_style = ParagraphStyle(
            "SuccessText",
            parent=self.body_style,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#047857"),
        )

    def generate_pdf(
        self,
        project: Project,
        output_filepath: str,
        watermark_text: Optional[str] = None,
        license_data: Optional[Any] = None,
    ) -> str:
        """Gera o arquivo PDF da Memória de Cálculo Estrutural com demonstração passo a passo."""
        if project.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem exportar Memória de Cálculo.")

        if license_data is not None:
            license_data.assert_can_export_pdf()

        if not output_filepath.lower().endswith(".pdf"):
            output_filepath += ".pdf"

        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)

        doc = SimpleDocTemplate(
            output_filepath,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        story = []
        usable_width = A4[0] - 72

        # 1. Cabeçalho Institucional
        story.append(Paragraph("MEMÓRIA DE CÁLCULO ESTRUTURAL — LINHA DE VIDA HORIZONTAL", self.title_style))
        story.append(Spacer(1, 2))
        story.append(
            Paragraph(
                "Dimensionamento Conforme Diretrizes da NR-35, ABNT NBR 16325-1 / NBR 16325-2 e ABNT NBR ISO 2408",
                self.subtitle_style,
            )
        )
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=8))

        # 2. Dados de Identificação do Projeto
        story.append(Paragraph("1. DADOS DE IDENTIFICAÇÃO DO PROJETO", self.section_heading))
        date_str = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M UTC")

        data_id = [
            [
                Paragraph("<b>Título do Projeto:</b>", self.body_style),
                Paragraph(project.title, self.body_style),
                Paragraph("<b>Código / ID:</b>", self.body_style),
                Paragraph(project.project_id, self.body_style),
            ],
            [
                Paragraph("<b>Cliente / Empresa:</b>", self.body_style),
                Paragraph(project.client, self.body_style),
                Paragraph("<b>Data da Emissão:</b>", self.body_style),
                Paragraph(date_str, self.body_style),
            ],
            [
                Paragraph("<b>Local da Instalação:</b>", self.body_style),
                Paragraph(project.location, self.body_style),
                Paragraph("<b>Status do Projeto:</b>", self.body_style),
                Paragraph(f"<b>{project.status.value}</b>", self.success_style if project.status == ProjectStatus.CALCULATED_VALID else self.danger_style),
            ],
            [
                Paragraph("<b>Responsável Técnico:</b>", self.body_style),
                Paragraph(project.responsible_engineer, self.body_style),
                Paragraph("<b>Versão do Sistema:</b>", self.body_style),
                Paragraph(f"v{project.schema_version}", self.body_style),
            ],
        ]

        t_id = Table(data_id, colWidths=[105, 155, 105, usable_width - 365])
        t_id.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_id)
        story.append(Spacer(1, 8))

        # 3. Dados da Instalação Física e Estrutural
        story.append(Paragraph("2. CONDIÇÕES ESTRUTURAIS E TIPO DE INSTALAÇÃO", self.section_heading))
        inst = project.installation

        data_inst = [
            [
                Paragraph("<b>Tipo de Aplicação:</b>", self.body_style),
                Paragraph(inst.category.value, self.bold_style),
                Paragraph("<b>ART da Estrutura:</b>", self.body_style),
                Paragraph(inst.responsible_engineer_art or "Pendente de validação", self.body_style),
            ]
        ]
        t_inst = Table(data_inst, colWidths=[105, 155, 105, usable_width - 365])
        t_inst.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_inst)
        story.append(Spacer(1, 8))

        # 4. Parâmetros do Cabo e Critérios de Carregamento
        story.append(Paragraph("3. PARÂMETROS DO CABO DE AÇO E HIPÓTESE DE CARREGAMENTO", self.section_heading))
        cabo = project.cable
        u_cfg = project.user_config

        if cabo:
            cabo_spec_text = cabo.specification
            cabo_d_text = f"{cabo.diameter_mm:.1f} mm"
            cabo_am_text = f"{cabo.metallic_area_mm2:.2f} mm² (F = {cabo.metallic_area_factor})"
            cabo_e_text = f"{cabo.elastic_modulus_kgf_mm2:,.0f} kgf/mm² (~{cabo.elastic_modulus_mpa:,.0f} MPa)"
            cabo_fu_text = f"{cabo.min_breaking_load_kgf:,.2f} kgf ({cabo.min_breaking_load_kn:.2f} kN)"
        else:
            cabo_spec_text = cabo_d_text = cabo_am_text = cabo_e_text = cabo_fu_text = "Não definido"

        p_kgf = u_cfg.calculated_design_load_kgf
        p_kn = (p_kgf * 9.80665) / 1000.0

        data_cabo_carga = [
            [
                Paragraph("<b>Cabo de Aço:</b>", self.body_style),
                Paragraph(cabo_spec_text, self.bold_style),
                Paragraph("<b>Carga de Cálculo P:</b>", self.body_style),
                Paragraph(f"<b>{p_kgf:.1f} kgf ({p_kn:.2f} kN)</b>", self.bold_style),
            ],
            [
                Paragraph("<b>Diâmetro Nominal:</b>", self.body_style),
                Paragraph(cabo_d_text, self.body_style),
                Paragraph("<b>Regra de Usuários:</b>", self.body_style),
                Paragraph(u_cfg.rule_type.value, self.body_style),
            ],
            [
                Paragraph("<b>Área Metálica (Am):</b>", self.body_style),
                Paragraph(cabo_am_text, self.body_style),
                Paragraph("<b>Usuários Simultâneos:</b>", self.body_style),
                Paragraph(f"{u_cfg.simultaneous_users} pessoa(s) em queda", self.body_style),
            ],
            [
                Paragraph("<b>Módulo Elasticidade (E):</b>", self.body_style),
                Paragraph(cabo_e_text, self.body_style),
                Paragraph("<b>FS Mínimo Normativo:</b>", self.body_style),
                Paragraph(f"FS >= {project.min_safety_factor:.2f}", self.body_style),
            ],
            [
                Paragraph("<b>Força Mín. Ruptura (Fu):</b>", self.body_style),
                Paragraph(cabo_fu_text, self.bold_style),
                Paragraph("<b>Total de Postes / Vãos:</b>", self.body_style),
                Paragraph(f"{len(project.spans) + 1} postes / {len(project.spans)} vão(s)", self.body_style),
            ],
        ]

        t_cc = Table(data_cabo_carga, colWidths=[115, 145, 110, usable_width - 370])
        t_cc.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_cc)
        story.append(Spacer(1, 8))

        # 5. Resultados do Dimensionamento Estrutural
        story.append(Paragraph("4. RESULTADOS CONSOLIDADOS DO CÁLCULO E ESFORÇOS", self.section_heading))

        res = project.calculation_result
        if res:
            crit = res.critical_span_result

            # Tabela de Resultados por Vão
            header_res = ["Vão", "Comprimento (D)", "Flecha f1", "Alongamento ΔL", "Flecha f2", "Tração T", "Fator Seg. (FS)", "Status"]
            table_res_data = [[Paragraph(f"<b>{h}</b>", self.body_style) for h in header_res]]

            for idx, s_res in enumerate(res.span_results):
                geom = project.spans[idx]
                is_crit = (idx + 1 == res.critical_span_index)
                span_name = f"Vão {idx + 1}" + (" (*)" if is_crit else "")

                status_p = Paragraph(f"<b>{s_res.status_text}</b>", self.success_style if s_res.is_approved else self.danger_style)

                table_res_data.append([
                    Paragraph(span_name, self.bold_style if is_crit else self.body_style),
                    Paragraph(f"{geom.span_mm:,.0f} mm", self.body_style),
                    Paragraph(f"{s_res.initial_sag_mm:.1f} mm", self.body_style),
                    Paragraph(f"{s_res.elongation_mm:.2f} mm", self.body_style),
                    Paragraph(f"<b>{s_res.dynamic_sag_mm:.1f} mm</b>", self.body_style),
                    Paragraph(f"<b>{s_res.tension_kgf:,.0f} kgf</b>", self.body_style),
                    Paragraph(f"<b>{s_res.safety_factor:.3f}</b>", self.success_style if s_res.safety_factor >= project.min_safety_factor else self.danger_style),
                    status_p,
                ])

            t_res = Table(table_res_data, colWidths=[65, 75, 55, 65, 65, 65, 65, usable_width - 455])
            t_res.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ALIGN", (1, 0), (-2, -1), "CENTER"),
            ]))
            story.append(t_res)
            story.append(Spacer(1, 4))

            # Resumo de Esforços nas Ancoragens
            t_ext_kn = (res.end_anchor_load_kgf * 9.80665) / 1000.0
            data_esforcos = [
                [
                    Paragraph("<b>Tração nas Ancoragens de Extremidade:</b>", self.body_style),
                    Paragraph(f"<b>{res.end_anchor_load_kgf:,.0f} kgf ({t_ext_kn:.2f} kN)</b>", self.bold_style),
                    Paragraph("<b>Vão Crítico:</b>", self.body_style),
                    Paragraph(f"Vão {res.critical_span_index} ({project.spans[res.critical_span_index - 1].span_mm:.0f} mm)", self.body_style),
                ],
                [
                    Paragraph("<b>Carga Vertical nos Postes Intermediários:</b>", self.body_style),
                    Paragraph(f"{res.intermediate_post_vertical_load_kgf:,.0f} kgf", self.body_style),
                    Paragraph("<b>Carga Horizontal nos Intermediários:</b>", self.body_style),
                    Paragraph(f"{res.intermediate_post_horizontal_load_kgf:,.0f} kgf", self.body_style),
                ],
            ]
            t_esf = Table(data_esforcos, colWidths=[170, 110, 100, usable_width - 380])
            t_esf.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(t_esf)
        else:
            story.append(Paragraph("Cálculo ainda não executado.", self.body_style))

        story.append(Spacer(1, 8))

        # =========================================================================
        # 6. DEMONSTRAÇÃO ANALÍTICA E MEMÓRIA DE CÁLCULO PASSO A PASSO (NOVO)
        # =========================================================================
        story.append(Paragraph("5. DEMONSTRAÇÃO ANALÍTICA E FORMULAÇÃO MATEMÁTICA", self.section_heading))

        # Sub-seção 5.1: Equações Normativas Empregadas
        story.append(Paragraph("5.1. Formulação Teórica e Equações Normativas Empregadas", self.sub_heading))

        data_formulas = [
            [
                Paragraph("<b>Item / Fenômeno</b>", self.body_style),
                Paragraph("<b>Equação Matemática Literal</b>", self.body_style),
                Paragraph("<b>Descrição / Norma de Referência</b>", self.body_style),
            ],
            [
                Paragraph("<b>1. Geometria Inicial (L<sub>1</sub>)</b>", self.body_style),
                Paragraph("L<sub>1</sub> = 2 · raiz[ (D / 2)<sup>2</sup> + f<sub>1</sub><sup>2</sup> ]", self.formula_expr),
                Paragraph("Comprimento do cabo com flecha inicial f<sub>1</sub> = %f · D sob pré-tensão de montagem.", self.body_style),
            ],
            [
                Paragraph("<b>2. Carga de Cálculo (P)</b>", self.body_style),
                Paragraph("P = P<sub>din</sub> + (n - 1) · P<sub>est</sub>", self.formula_expr),
                Paragraph("NBR 16325-2: P<sub>din</sub> = 600 kgf (6 kN, 1º trab.) + 100 kgf (1 kN/adicional).", self.body_style),
            ],
            [
                Paragraph("<b>3. Geometria Deformada (L<sub>2</sub>)</b>", self.body_style),
                Paragraph("L<sub>2</sub> = 2 · raiz[ (D / 2)<sup>2</sup> + f<sub>2</sub><sup>2</sup> ]", self.formula_expr),
                Paragraph("Comprimento deformado sob flecha dinâmica vertical máxima f<sub>2</sub> no impacto.", self.body_style),
            ],
            [
                Paragraph("<b>4. Alongamento Elástico (ΔL)</b>", self.body_style),
                Paragraph("ΔL = L<sub>2</sub> - L<sub>1</sub>", self.formula_expr),
                Paragraph("Esticamento físico longitudinal do cabo de aço provocado pela carga de queda.", self.body_style),
            ],
            [
                Paragraph("<b>5. Equilíbrio Elasto-Geométrico</b>", self.body_style),
                Paragraph("(E · A<sub>m</sub> · ΔL) / L<sub>1</sub> = (P · L<sub>2</sub>) / (4 · f<sub>2</sub>)", self.formula_expr),
                Paragraph("Lei de Hooke (rigidez axial) = Estática no vértice. Resolvido por bissecção.", self.body_style),
            ],
            [
                Paragraph("<b>6. Fator de Segurança (FS)</b>", self.body_style),
                Paragraph("FS = F<sub>u</sub> / T  &gt;=  2,00", self.formula_expr),
                Paragraph("NBR 16325-2 e NBR ISO 2408: F<sub>u</sub> = carga de ruptura mínima; T = tração atuante.", self.body_style),
            ],
            [
                Paragraph("<b>7. Zona Livre de Queda (ZLQ)</b>", self.body_style),
                Paragraph("ZLQ = L<sub>tala</sub> + E<sub>abs</sub> + H<sub>trab</sub> + f<sub>2</sub> + M<sub>seg</sub>", self.formula_expr),
                Paragraph("NR-35 Anexo II: M<sub>seg</sub> = 1,00 m (obrigatória). Margem residual: M<sub>res</sub> = H<sub>disp</sub> - ZLQ.", self.body_style),
            ],
        ]

        t_form = Table(data_formulas, colWidths=[120, 200, usable_width - 320])
        t_form.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0369a1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_form)
        story.append(Spacer(1, 6))

        # Sub-seção 5.2: Demonstração Numérica Passo a Passo com Variáveis Reais do Projeto
        if res and res.critical_span_result and project.cable:
            story.append(Paragraph("5.2. Memória Numérica Passo a Passo — Aplicação no Vão Crítico", self.sub_heading))

            crit_idx = res.critical_span_index
            crit_geom = project.spans[crit_idx - 1]
            crit_res = res.critical_span_result

            D_mm = crit_geom.span_mm
            f1_mm = crit_res.initial_sag_mm
            L1_mm = 2.0 * math.sqrt((D_mm / 2.0) ** 2 + f1_mm ** 2)

            c_d = cabo.diameter_mm
            c_Am = cabo.metallic_area_mm2
            c_E = cabo.elastic_modulus_kgf_mm2
            c_Fu = cabo.min_breaking_load_kgf

            f2_mm = crit_res.dynamic_sag_mm
            L2_mm = 2.0 * math.sqrt((D_mm / 2.0) ** 2 + f2_mm ** 2)
            dL_mm = crit_res.elongation_mm
            T_kgf = crit_res.tension_kgf
            T_kn = (T_kgf * 9.80665) / 1000.0
            FS_calc = crit_res.safety_factor

            # ZLQ
            inp_zlq = project.clearance_input
            l_tala = inp_zlq.lanyard_length_m
            e_abs = inp_zlq.absorber_extension_m
            h_trab = inp_zlq.worker_height_offset_m
            m_seg = inp_zlq.safety_margin_m
            f2_m = f2_mm / 1000.0
            zlq_tot = l_tala + e_abs + h_trab + f2_m + m_seg
            h_disp = inp_zlq.available_clearance_m
            m_res = (h_disp - zlq_tot) if h_disp is not None else None

            data_passos = [
                [
                    Paragraph("<b>Passo 1: Comprimento Inicial Montado (L<sub>1</sub>)</b>", self.step_label),
                    Paragraph(f"L<sub>1</sub> = 2 · raiz[ ({D_mm:,.1f} / 2)<sup>2</sup> + ({f1_mm:.1f})<sup>2</sup> ] = <b>{L1_mm:,.2f} mm</b> ({L1_mm/1000.0:.3f} m)", self.step_math),
                ],
                [
                    Paragraph("<b>Passo 2: Carga de Projeto Aplicada (P)</b>", self.step_label),
                    Paragraph(f"P = {u_cfg.dynamic_load_first_user_kgf:.1f} + ({u_cfg.simultaneous_users} - 1) · {u_cfg.static_load_per_additional_kgf:.1f} = <b>{p_kgf:.1f} kgf</b> ({p_kn:.2f} kN)", self.step_math),
                ],
                [
                    Paragraph("<b>Passo 3: Propriedades Seccionais do Cabo</b>", self.step_label),
                    Paragraph(f"Diâmetro = {c_d:.1f} mm | A<sub>m</sub> = {c_Am:.2f} mm² | E = {c_E:,.0f} kgf/mm² | F<sub>u</sub> = <b>{c_Fu:,.2f} kgf</b>", self.step_math),
                ],
                [
                    Paragraph("<b>Passo 4: Flecha Dinâmica e Esticamento (ΔL)</b>", self.step_label),
                    Paragraph(f"f<sub>2</sub> = <b>{f2_mm:.1f} mm</b> ({f2_m:.3f} m)  &rarr;  L<sub>2</sub> = 2 · raiz[ ({D_mm:,.1f}/2)<sup>2</sup> + ({f2_mm:.1f})<sup>2</sup> ] = {L2_mm:,.2f} mm<br/>"
                              f"Alongamento Elástico: ΔL = L<sub>2</sub> - L<sub>1</sub> = {L2_mm:,.2f} - {L1_mm:,.2f} = <b>{dL_mm:.2f} mm</b> ({dL_mm/1000.0:.4f} m)", self.step_math),
                ],
                [
                    Paragraph("<b>Passo 5: Tração Dinâmica Atuante (T)</b>", self.step_label),
                    Paragraph(f"T = (E · A<sub>m</sub> · ΔL) / L<sub>1</sub> = ({c_E:,.0f} · {c_Am:.2f} · {dL_mm:.2f}) / {L1_mm:,.2f} = <b>{T_kgf:,.1f} kgf</b> ({T_kn:.2f} kN)", self.step_math),
                ],
                [
                    Paragraph("<b>Passo 6: Fator de Segurança (FS)</b>", self.step_label),
                    Paragraph(f"FS = F<sub>u</sub> / T = {c_Fu:,.2f} / {T_kgf:,.1f} = <b>{FS_calc:.3f}</b>  " +
                              (f"&gt;= {project.min_safety_factor:.2f} &rarr; <font color='#047857'><b>CONFORME (APROVADO)</b></font>" if FS_calc >= project.min_safety_factor else f"&lt; {project.min_safety_factor:.2f} &rarr; <font color='#b91c1c'><b>NÃO CONFORME (REPROVADO)</b></font>"), self.step_math),
                ],
                [
                    Paragraph("<b>Passo 7: Zona Livre de Queda (NR-35)</b>", self.step_label),
                    Paragraph(f"ZLQ = {l_tala:.2f} + {e_abs:.2f} + {h_trab:.2f} + {f2_m:.2f} (f<sub>2</sub>) + {m_seg:.2f} = <b>{zlq_tot:.2f} m</b><br/>"
                              f"Altura Disp. (H<sub>disp</sub>) = {f'{h_disp:.2f} m' if h_disp else 'Não informada'} | "
                              f"Margem Res. = {f'{m_res:+.2f} m' if m_res is not None else '-'} &rarr; " +
                              ("<font color='#047857'><b>APROVADO (Sem Risco de Colisão)</b></font>" if (m_res is not None and m_res >= 0) else "<font color='#b91c1c'><b>REPROVADO (RISCO DE COLISÃO)</b></font>"), self.step_math),
                ],
            ]

            t_passos = Table(data_passos, colWidths=[160, usable_width - 160])
            t_passos.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(t_passos)

        story.append(Spacer(1, 8))

        # 7. Verificação de Zona Livre de Queda (NR-35)
        story.append(Paragraph("6. RESUMO DA VERIFICAÇÃO DE ZONA LIVRE DE QUEDA (NR-35)", self.section_heading))
        cl_res = crit.clearance_result if (res and crit and crit.clearance_result) else None

        if cl_res:
            h_disp_text = f"{cl_res.available_clearance_m:.2f} m" if cl_res.available_clearance_m else "Não informada"
            margin_text = f"{cl_res.residual_margin_m:+.2f} m" if cl_res.residual_margin_m is not None else "-"
            parecer_zlq = "APROVADO (Sem colisão)" if cl_res.clearance_approved else "REPROVADO (RISCO DE COLISÃO)"

            data_zlq = [
                [
                    Paragraph("<b>ZLQ Requerida Total:</b>", self.body_style),
                    Paragraph(f"<b>{cl_res.required_clearance_m:.2f} m</b>", self.bold_style),
                    Paragraph("<b>Altura Disponível (Hdisp):</b>", self.body_style),
                    Paragraph(h_disp_text, self.body_style),
                ],
                [
                    Paragraph("<b>Flecha Dinâmica do Cabo (f2):</b>", self.body_style),
                    Paragraph(f"{cl_res.dynamic_sag_m:.2f} m", self.body_style),
                    Paragraph("<b>Margem Livre Residual:</b>", self.body_style),
                    Paragraph(margin_text, self.success_style if cl_res.clearance_approved else self.danger_style),
                ],
                [
                    Paragraph("<b>Parecer de ZLQ:</b>", self.body_style),
                    Paragraph(f"<b>{parecer_zlq}</b>", self.success_style if cl_res.clearance_approved else self.danger_style),
                    Paragraph("<b>Margem Normativa NR-35:</b>", self.body_style),
                    Paragraph("1,00 m (obrigatória)", self.body_style),
                ],
            ]
            t_zlq = Table(data_zlq, colWidths=[120, 140, 110, usable_width - 370])
            t_zlq.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(t_zlq)

        story.append(Spacer(1, 8))

        # 8. Ilustração Explicativa / Diagrama ZLQ (ESTRITAMENTE CENTRALIZADO)
        img_path = resolve_image_path("zlq.jpg")
        if os.path.exists(img_path):
            story.append(PageBreak())
            story.append(Paragraph("7. ESQUEMA TÉCNICO ILUSTRATIVO DE ZONA LIVRE DE QUEDA", self.section_heading))
            try:
                from PIL import Image as PILImage
                with PILImage.open(img_path) as im:
                    orig_w, orig_h = im.size

                # Largura controlada e estritamente centralizada na página
                target_w = min(440.0, usable_width)
                aspect = orig_h / orig_w
                target_h = target_w * aspect

                img_flowable = Image(img_path, width=target_w, height=target_h, hAlign="CENTER")
                story.append(Spacer(1, 4))
                story.append(img_flowable)
                story.append(Spacer(1, 10))
            except Exception:
                pass

        # 8. Especificação de Materiais e Componentes (BOM)
        if project.can_generate_bom:
            try:
                bom = project.generate_bom()
                story.append(Paragraph("8. ESPECIFICAÇÃO DE MATERIAIS E COMPONENTES (BOM)", self.section_heading))

                header_bom = ["Item", "Código", "Componente / Especificação", "Qtd.", "Un.", "Instrução de Montagem"]
                table_bom_data = [[Paragraph(f"<b>{h}</b>", self.body_style) for h in header_bom]]

                for idx, it in enumerate(bom.items, start=1):
                    table_bom_data.append([
                        Paragraph(str(idx), self.body_style),
                        Paragraph(f"<b>{it.item_code}</b>", self.bold_style),
                        Paragraph(f"<b>{it.name}</b><br/>{it.specification}", self.body_style),
                        Paragraph(f"<b>{it.quantity:,.1f}</b>" if it.quantity % 1 != 0 else f"<b>{int(it.quantity)}</b>", self.bold_style),
                        Paragraph(it.unit, self.body_style),
                        Paragraph(it.technical_notes, self.body_style),
                    ])

                t_bom_pdf = Table(table_bom_data, colWidths=[25, 55, 175, 40, 30, usable_width - 325])
                t_bom_pdf.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (3, 0), (4, -1), "CENTER"),
                ]))
                story.append(t_bom_pdf)
                story.append(Spacer(1, 8))
            except Exception:
                pass

        # 9. Parecer Técnico e Assinatura
        sec_num = "9" if project.can_generate_bom else "8"
        story.append(Paragraph(f"{sec_num}. PARECER TÉCNICO E TERMO DE RESPONSABILIDADE", self.section_heading))

        if project.status == ProjectStatus.CALCULATED_VALID:
            status_desc = (
                "A linha de vida horizontal flexível descrita neste relatório ATENDE aos requisitos "
                "de segurança mecânica e flecha admissível estipulados pelas normas ABNT NBR 16325-1, "
                "ABNT NBR 16325-2 e NR-35. O fator de segurança nominal do cabo de aço é superior ao limite mínimo de 2,00 "
                "e a Zona Livre de Queda garante a retenção segura sem colisão com o piso ou obstáculos."
            )
            story.append(Paragraph(f"<b>STATUS FINAL: APROVADO</b>", self.success_style))
        else:
            rejection = res.rejection_reason if res else "Cálculo pendente ou não aprovado."
            status_desc = f"STATUS FINAL: REPROVADO OU PENDENTE. Motivo: {rejection}"
            story.append(Paragraph(f"<b>STATUS FINAL: REPROVADO / NÃO CONFORME</b>", self.danger_style))

        story.append(Spacer(1, 3))
        story.append(Paragraph(status_desc, self.body_style))
        story.append(Spacer(1, 12))

        # Bloco de Assinatura
        data_sig = [
            [
                Paragraph("<b>Local e Data:</b>", self.body_style),
                Paragraph(f"{project.location}, {datetime.now(timezone.utc).strftime('%d de %B de %Y')}", self.body_style),
            ],
            [
                Paragraph("<b>Responsável Técnico:</b>", self.body_style),
                Paragraph(f"{project.responsible_engineer}<br/>Engenheiro Responsável Técnico<br/>CREA / ART: {project.installation.responsible_engineer_art or 'A preencher'}", self.body_style),
            ],
            [
                Paragraph("<b>Assinatura:</b>", self.body_style),
                Paragraph("<br/><br/>____________________________________________________<br/>Assinatura do Responsável Técnico", self.body_style),
            ],
        ]
        t_sig = Table(data_sig, colWidths=[120, usable_width - 120])
        t_sig.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(KeepTogether(t_sig))

        # Determina a marca d'água apropriada se não for fornecida explicitamente
        if watermark_text is None:
            try:
                from src.core.license_manager import LicenseManager
                lic = LicenseManager().get_license()
                if lic.watermark_text:
                    watermark_text = lic.watermark_text
                elif not lic.is_pro:
                    watermark_text = "USO COMUNITÁRIO / NÃO COMERCIAL"
            except Exception:
                pass

        # Compila o PDF com o NumberedCanvas para numeração dinâmica de páginas, rodapé e marca d'água
        canvas_factory = make_numbered_canvas(watermark_text) if watermark_text else NumberedCanvas
        doc.build(story, canvasmaker=canvas_factory)
        return output_filepath
