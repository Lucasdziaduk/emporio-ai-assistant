# M5 — conteúdo consolidado

O M5 completo (incluindo os overlays Groq, M5.1 e M5.2) contém:

- `app/agent/`: CLI, runtime, prompt, sessão e controles de privacidade.
- `app/llm/`: contrato neutro, adaptador Gemini Interactions e adaptador OpenAI-compatible para Groq.
- `app/tools/`: registry allow-list e seis ferramentas da loja.
- `requirements-m5.txt`: SDK opcional Google Gen AI.
- `requirements-m5-groq.txt`: cliente Python OpenAI-compatible usado com Groq.
- `examples/M5_CONVERSATIONS.md`: quatro exemplos de interação.
- `M5_README.md`, `M5_GROQ_QUICKSTART.md` e `M5_TEST_REPORT.md`: documentação do agente e provedor.
- `M5_1_POLICY_CONFLICT_HOTFIX.md`: barreira determinística para políticas ambíguas.
- `M5_2_PRODUCT_DETAIL_FIDELITY.md`: formatação determinística das especificações do catálogo.

O repositório público não deve conter `.env`, `.venv`, banco SQLite local, CSVs originais, dados pessoais de clientes ou o manual PDF restrito.
