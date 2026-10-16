# LineLife — public code review snapshot

Snapshot local do software desktop LineLife para inspeção técnica, validação de cálculos e reprodução de testes.

O snapshot contém somente código Python, testes selecionados e assets necessários. Não contém site, landing page, VPS, dados operacionais, skills, histórico privado, serviços externos ou configuração de produção.

## Executar no Windows

Requer Python 3.12.

```powershell
py -3.12 -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.\\.venv\\Scripts\\python.exe run_desktop.py
```

## Testes

```powershell
.\\.venv\\Scripts\\python.exe -m unittest discover tests -v
```

A execução padrão é local e não inicia telemetria, heartbeat, VPS ou outro serviço externo.

## Escopo

Este snapshot é destinado exclusivamente à consulta técnica e à tentativa independente de replicação. Não há canal de suporte, promessa de manutenção, correção de problemas, compatibilidade com ambientes de terceiros ou resposta a solicitações de implementação.

## Licença

Consulte `LICENSE`.
