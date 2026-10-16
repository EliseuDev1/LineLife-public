"""Utilitários para localização de recursos estáticos (imagens, catálogos, ícones).

Garante compatibilidade total entre:
1. Execução em ambiente de desenvolvimento local (código-fonte Python).
2. Execução empacotada como executável autônomo PyInstaller (.exe) via sys._MEIPASS.
"""

import os
import sys
from typing import List, Optional


def get_base_dir() -> str:
    """Retorna o diretório raiz dos recursos do aplicativo."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    # Diretório raiz do projeto (onde está o package src)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def get_resource_path(relative_path: str) -> str:
    """Localiza o caminho absoluto de um recurso testando múltiplos locais candidatos."""
    base_dir = get_base_dir()
    
    candidates = [
        # 1. Caminho direto relativo ao base_dir
        os.path.abspath(os.path.join(base_dir, relative_path)),
        # 2. Caminho dentro da pasta projeto_linha_vida
        os.path.abspath(os.path.join(base_dir, "projeto_linha_vida", relative_path)),
        # 3. Caminho dentro de src
        os.path.abspath(os.path.join(base_dir, "src", relative_path)),
        # 4. Diretório de trabalho atual (CWD)
        os.path.abspath(os.path.join(os.getcwd(), relative_path)),
        # 5. CWD com subpasta projeto_linha_vida
        os.path.abspath(os.path.join(os.getcwd(), "projeto_linha_vida", relative_path)),
    ]

    for c in candidates:
        if os.path.exists(c):
            return c

    # Fallback para o primeiro candidato
    return candidates[0]


def get_app_data_dir(app_name: str = "LinhaDeVida") -> str:
    """Retorna o diretório local de dados do usuário (ex: %APPDATA%/LinhaDeVida)."""
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        app_data = os.path.expanduser("~/.config")
    
    target_dir = os.path.join(app_data, app_name)
    os.makedirs(target_dir, exist_ok=True)
    return target_dir
