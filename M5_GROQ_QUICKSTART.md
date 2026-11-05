# M5 — Alternar Gemini para Groq

Este overlay mantém o adaptador Gemini e adiciona um adaptador compatível com a API Chat Completions da OpenAI, usando Groq como provedor padrão.

## Modelo configurado

- Provider: Groq
- Model: `openai/gpt-oss-20b`
- API base: `https://api.groq.com/openai/v1`
- Function calling: executado localmente pelo `AgentRuntime`, com a mesma lista de seis ferramentas e validação M2–M4.

O GPT-OSS 20B foi escolhido porque aparece na lista oficial de modelos de produção da Groq e tem suporte documentado a local/remote tool use. Modelos Llama 3.3 70B e 3.1 8B estão indicados como Enterprise na tabela atual da Groq. Consulte o catálogo e a documentação antes de fixar um modelo em produção.

## Configuração

1. Crie uma chave em https://console.groq.com/keys.
2. Abra `.env` na raiz do projeto e adicione/ajuste:

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=sua_chave_groq
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

Mantenha as variáveis `GEMINI_API_KEY` e `GEMINI_MODEL` se quiser voltar ao Gemini depois. Nunca publique `.env` ou compartilhe a chave.

3. Instale o cliente no ambiente virtual ativado:

```powershell
python -m pip install -r requirements-m5-groq.txt
```

4. Rode os testes:

```powershell
python -m pytest -q
```

5. Inicie:

```powershell
python -m app.agent
```

O terminal deve indicar `Provedor: groq. Modelo: openai/gpt-oss-20b.`

## Voltar ao Gemini

Altere no `.env`:

```dotenv
LLM_PROVIDER=gemini
```

O `GEMINI_API_KEY` e o `GEMINI_MODEL` originais serão usados. Não é preciso remover a dependência OpenAI.

## Observações de segurança e custo

- O telefone de verificação de pedido continua sendo interceptado e validado localmente pelo runtime; ele não entra no histórico enviado ao modelo.
- As mensagens, o prompt do sistema, as declarações de ferramentas e os resultados necessários às respostas são enviados ao provedor configurado. Revise os termos e as configurações de retenção do provedor antes de qualquer implantação com dados reais.
- A API da Groq é paga conforme modelo/conta e limites vigentes. Consulte o console e a página de modelos; não presuma que a API seja ilimitada ou gratuita.
- O adaptador usa timeout de 25 segundos e uma repetição automática do SDK para limitar esperas prolongadas.
- Os testes do adaptador usam um cliente simulado e não substituem uma chamada real com sua chave Groq.
