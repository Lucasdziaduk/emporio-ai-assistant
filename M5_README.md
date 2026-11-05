# M5 — Agente Conversacional, Function Calling e Orquestração

M5 conecta a camada de dados (M2), os serviços de negócio (M3) e a recuperação de políticas (M4) a um agente conversacional em Python.

## Provedor usado na entrega

A execução principal usa **Groq** com o modelo `openai/gpt-oss-20b`, via API Chat Completions compatível com OpenAI. O adaptador Gemini Interactions permanece como alternativa selecionável por `LLM_PROVIDER`.

Consulte o [README principal](README.md) para requisitos, instalação, cópia dos dados privados, configuração completa, execução, arquitetura, decisões técnicas, limitações e uso de assistentes de código.

## Seis ferramentas disponíveis

1. `search_products`
2. `get_product_details`
3. `get_order_status`
4. `search_store_policies`
5. `get_store_information`
6. `get_purchase_conditions`

O modelo não consulta o banco diretamente. As funções são declaradas em uma allow-list, os argumentos são validados e os handlers chamam a camada de serviços existente.

## Segurança

- O telefone usado na consulta de pedido é capturado e validado localmente; não é enviado ao provedor nem incluído no histórico.
- Mensagens comuns com telefone são mascaradas antes de entrar no histórico.
- Consultas de política com conflito não resolvido são interrompidas por uma barreira determinística do runtime e encaminhadas para confirmação humana.
- Fichas de produto são formatadas diretamente a partir de campos conhecidos do catálogo, evitando que o LLM reinterprete especificações técnicas.

## Configuração rápida do provedor Groq

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=sua_chave
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

Instale e execute na raiz do projeto:

```powershell
python -m pip install -r requirements-m5-groq.txt
python -m app.agent
```

Para executar a suíte:

```powershell
python -m pytest -q
```

O histórico da sessão é mantido em memória e se perde ao encerrar a CLI. O protótipo não possui interface web, CRM, checkout, sincronização de estoque ou integração de atendimento humano.
