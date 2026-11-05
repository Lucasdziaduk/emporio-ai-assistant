"""Run the Empório da Música terminal agent with Gemini or Groq."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from app.agent import AgentRuntime, AgentSession
from app.data import create_connection, load_dataset
from app.services.container import build_service_container


def _build_model():
    provider = os.getenv("LLM_PROVIDER", "gemini").strip().casefold()
    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip()
        if not api_key:
            raise ValueError("Configuração ausente: defina GROQ_API_KEY no arquivo .env.")
        from app.llm.openai_compatible import OpenAICompatibleToolClient

        return provider, model_name, OpenAICompatibleToolClient(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
            timeout=25.0,
            max_retries=1,
        )

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
        if not api_key:
            raise ValueError("Configuração ausente: defina GEMINI_API_KEY no arquivo .env.")
        from app.llm.gemini_interactions import GeminiInteractionsClient

        return provider, model_name, GeminiInteractionsClient(
            api_key=api_key,
            model_name=model_name,
        )

    raise ValueError("LLM_PROVIDER inválido. Use 'gemini' ou 'groq'.")


def main() -> int:
    project_root = Path.cwd()
    load_dotenv(project_root / ".env")
    source_dir = Path(os.getenv("DATA_SOURCE_DIR", "data/private/source"))
    policy_pdf = Path(os.getenv("POLICY_PDF_PATH", "data/private/store_policies.pdf"))
    database_path = Path(os.getenv("DATABASE_PATH", "data/private/emporio.sqlite3"))

    try:
        provider, model_name, model = _build_model()
    except (ValueError, RuntimeError) as exc:
        print(str(exc))
        return 2

    if not source_dir.is_dir():
        print(f"Pasta de dados não encontrada: {source_dir}")
        return 2
    if not policy_pdf.is_file():
        print(f"Manual da loja não encontrado: {policy_pdf}")
        return 2

    connection = create_connection(database_path)
    try:
        report = load_dataset(source_dir, connection)
        services = build_service_container(connection, policy_pdf_path=policy_pdf)
        agent = AgentRuntime(services=services, model=model)
        session = AgentSession.new()
        print("Empório da Música — atendimento virtual")
        print("Digite 'sair' para encerrar. A sessão fica somente em memória.\n")
        print(
            f"Base carregada: {sum(report.table_counts.values())} registros. "
            f"Provedor: {provider}. Modelo: {model_name}.\n"
        )
        while True:
            try:
                message = input("Você: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAtendimento encerrado.")
                break
            if message.casefold() in {"sair", "exit", "quit"}:
                print("Atendimento encerrado.")
                break
            if not message:
                continue
            print("Empório:", agent.respond(session, message), "\n")
    except Exception:
        print("Não foi possível iniciar o atendimento. Verifique os arquivos locais e a configuração.")
        return 1
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
