"""Módulo de persistência local para arquivos de projeto .lvd (Linha de Vida Document).

Garante que os projetos sejam salvos e lidos 100% offline, de forma atômica
e com validação de integridade de esquema, sem dependência de Excel ou banco de dados externo.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from src.domain.project import Project, ProjectStatus


LVD_FILE_FORMAT_HEADER = "LINHA_DE_VIDA_DOCUMENT"
LVD_CURRENT_SCHEMA_VERSION = "1.0.0"


class ProjectSerializer:
    """Gerenciador de serialização e persistência de arquivos .lvd."""

    @staticmethod
    def save_to_file(project: Project, filepath: str) -> None:
        """Salva o projeto em arquivo .lvd de forma atômica."""
        if project.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser salvos.")

        if not filepath.lower().endswith(".lvd"):
            filepath += ".lvd"

        envelope = {
            "format": LVD_FILE_FORMAT_HEADER,
            "version": LVD_CURRENT_SCHEMA_VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "data": project.to_dict(),
        }

        # Gravação atômica via arquivo temporário
        temp_path = f"{filepath}.tmp"
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(envelope, f, indent=2, ensure_ascii=False)

        if os.path.exists(filepath):
            os.replace(temp_path, filepath)
        else:
            os.rename(temp_path, filepath)

        project.is_dirty = False

    @staticmethod
    def load_from_file(filepath: str) -> Project:
        """Carrega e valida um projeto a partir de um arquivo .lvd."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo de projeto não encontrado: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            envelope = json.load(f)

        if envelope.get("format") != LVD_FILE_FORMAT_HEADER:
            raise ValueError(f"Formato de arquivo inválido: cabeçalho '{envelope.get('format')}' incompatível com .lvd")

        version = envelope.get("version")
        if version != LVD_CURRENT_SCHEMA_VERSION:
            raise ValueError(
                f"Versão .lvd incompatível: {version!r}. "
                "O projeto original foi preservado; abra-o em uma versão compatível."
            )

        project_data = envelope.get("data", {})
        project = Project.from_dict(project_data)
        project.is_dirty = False
        return project

    @staticmethod
    def clone(project: Project, new_title: Optional[str] = None) -> Project:
        """Clona um projeto existente gerando um novo ID independente em estado de rascunho."""
        if project.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser duplicados ou clonados.")
        data = project.to_dict()
        data["project_id"] = str(uuid.uuid4())[:8]
        data["title"] = new_title or f"Cópia de {project.title}"
        data["created_at"] = datetime.now(timezone.utc).isoformat()
        data["updated_at"] = data["created_at"]
        data["status"] = ProjectStatus.DRAFT.value

        cloned_project = Project.from_dict(data)
        cloned_project.calculation_result = None
        cloned_project.is_dirty = True
        return cloned_project
