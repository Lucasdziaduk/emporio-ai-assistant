# M5 Groq overlay — conteúdo

- `app/llm/openai_compatible.py`: adaptador provider-neutral de chat completions e function calling.
- `app/agent/__main__.py`: seletor de provedor `LLM_PROVIDER=gemini|groq`.
- `requirements-m5-groq.txt`: dependência opcional `openai`.
- `tests/unit/test_openai_compatible_adapter_m5.py`: testes de schemas, tool calls, histórico e resultados de ferramentas.
- `M5_GROQ_QUICKSTART.md`: instruções de configuração, execução e retorno ao Gemini.

Overlay sobre M1–M5. Não contém `.env`, banco local, CSVs de clientes/pedidos ou PDF privado.
