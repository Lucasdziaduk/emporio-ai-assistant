# Empório da Música — Agente de Atendimento com IA

Protótipo de um agente conversacional em Python para apoiar o atendimento da Empório da Música, loja fictícia de instrumentos musicais de Campo Grande/MS. O projeto foi desenvolvido para o desafio técnico de AI Engineer da Artefact.

O agente conversa em português brasileiro, consulta dados estruturados do catálogo e das operações, recupera trechos do manual interno e usa ferramentas Python validadas para responder. O modelo não acessa o banco diretamente: ele solicita ferramentas específicas, e a aplicação executa as operações por meio da camada de serviços.

## Funcionalidades

- Atendimento conversacional em CLI, com persona cordial e objetiva.
- Busca de produtos por texto, categoria, faixa de preço e disponibilidade.
- Consulta determinística dos detalhes de um produto, incluindo especificações com rótulos derivados dos campos de origem.
- Consulta de condições de pagamento, com cálculo de PIX e parcelamento no código Python.
- Consulta de informações gerais da loja, como endereço e horário.
- Recuperação de políticas do PDF com identificação de seção e página.
- Registro de conflitos conhecidos do manual e encaminhamento determinístico de situações ambíguas para confirmação humana.
- Início de consulta de pedido por ferramenta e verificação local do telefone cadastrado antes de liberar o status.
- Alternância de provedor entre Groq (padrão recomendado para esta entrega) e Gemini por variáveis de ambiente.

## Arquitetura

```text
CLI (app.agent)
    |
    v
AgentRuntime + AgentSession
    |                |
    |                +--> LLM adapter (Groq ou Gemini)
    |
    +--> ToolRegistry (allow-list de 6 ferramentas)
             |
             v
       Services (M3)
         |       |
         |       +--> PolicyService --> PDF extractor --> chunker --> BM25 + Conflict Registry (M4)
         |
         +--> Catalog / Promotions / Payments / Orders / Identity / Store
                     |
                     v
                Repositories
                     |
                     v
                  SQLite
                     ^
                     |
               CSV loader (M2)
```

### Camadas e responsabilidades

| Camada | Responsabilidade |
|---|---|
| `app/domain/` | Modelos, enums, erros e schemas de entrada/saída. |
| `app/data/` | Banco SQLite, carga transacional dos CSVs e repositórios. |
| `app/services/` | Regras de catálogo, promoções, pagamento, pedidos, identidade, políticas e informações da loja. |
| `app/knowledge/` | Extração do PDF, chunking por seção, normalização em português, BM25, avaliação e conflitos. |
| `app/tools/` | Seis ferramentas permitidas, validação de argumentos e despacho para serviços. |
| `app/llm/` | Contrato independente do provedor e adaptadores Groq/OpenAI-compatible e Gemini. |
| `app/agent/` | Prompt, sessão, privacidade e orquestração do ciclo modelo-ferramenta. |

## Decisões técnicas

### Python e interface

Python é a linguagem principal, conforme a única restrição técnica obrigatória do desafio. A interface escolhida é uma CLI (`python -m app.agent`): reduz o escopo de infraestrutura e permite demonstrar o comportamento do agente diretamente. O desafio permite CLI, notebook, API ou UI simples e prioriza o funcionamento correto do agente.

### Estratégia de agente: LLM + ferramentas determinísticas

Foi adotada uma arquitetura híbrida. O LLM interpreta a intenção e decide quando solicitar uma ferramenta; o código Python valida os argumentos, executa a regra de negócio e devolve o resultado. O modelo não recebe acesso direto ao SQLite nem pode executar funções fora da allow-list.

As seis ferramentas são:

1. `search_products`
2. `get_product_details`
3. `get_order_status`
4. `search_store_policies`
5. `get_store_information`
6. `get_purchase_conditions`

Cálculos monetários, validação de identidade, regras comerciais e formatação de detalhes críticos são realizados no código, evitando depender de aritmética ou interpretação livre do modelo.

### Modelo e provedor

A execução principal desta entrega usa **Groq com `openai/gpt-oss-20b`**, acessado pelo SDK Python `openai` em endpoint compatível com Chat Completions. O Function Calling é executado localmente pelo `AgentRuntime`; as seis ferramentas e os serviços não mudam quando o provedor é alterado.

Um adaptador Gemini (Interactions API) permanece no código como alternativa. A seleção é feita por `LLM_PROVIDER=groq` ou `LLM_PROVIDER=gemini`. A opção Groq foi adotada durante a validação porque o endpoint Gemini configurado respondeu HTTP 503 por alta demanda; essa foi uma indisponibilidade observada no provedor, não uma falha das ferramentas locais.

### Recuperação de políticas (RAG)

O manual é extraído com PyMuPDF e dividido em chunks que preservam títulos, seções e páginas. A recuperação utiliza BM25 com normalização de acentos, stopwords e sinônimos específicos do domínio em português. A abordagem lexical foi escolhida por ser simples de reproduzir localmente, não exigir uma API de embeddings e facilitar a inspeção da evidência recuperada.

A avaliação do conjunto de 24 perguntas de referência obteve Recall@3 = 1,00 e MRR = 0,9792 na validação do M4. Esses números descrevem apenas esse conjunto pequeno e específico; não representam uma garantia de precisão para qualquer pergunta.

O RAG recupera evidências; não resolve por si só contradições comerciais ou jurídicas. Um registro de conflitos identifica tópicos que exigem confirmação humana. O runtime bloqueia a geração livre da resposta quando a ferramenta retorna `requires_human_review=true`.

### Sessões e persistência

O histórico de conversa permanece somente em memória durante a execução da CLI. Ao encerrar o programa, a sessão é perdida. Essa escolha reduz a retenção de dados pessoais no protótipo e está documentada como limitação; o desafio deixa a persistência do histórico a critério do desenvolvedor.

### Dados e tratamento

Os seis CSVs fornecidos foram carregados em SQLite. Os registros do conjunto são:

| Tabela | Registros |
|---|---:|
| Produtos | 65 |
| Categorias | 9 |
| Promoções | 25 |
| Clientes | 50 |
| Pedidos | 20 |
| Itens de pedido | 22 |
| **Total** | **191** |

Valores monetários são convertidos com `Decimal` para centavos inteiros, evitando erros de ponto flutuante. A carga é transacional e valida chaves, tipos, enums e relacionamentos. Foram mantidos avisos de qualidade da fonte: e-mail duplicado entre dois clientes e divergências entre totais históricos de dois pedidos e subtotais calculados a partir do catálogo atual. Os totais originais dos pedidos são preservados, pois podem refletir preços ou descontos históricos.

**Os arquivos são snapshots fornecidos para o desafio.** Estoque, promoções e status de pedidos não são consultados em tempo real nem sincronizados com um sistema da loja.

## Requisitos

- Python 3.12 ou superior.
- Conta/chave de API da Groq para executar o atendimento com o provedor configurado nesta entrega.
- Arquivos CSV e PDF do desafio, mantidos localmente fora do repositório público.

## Configuração local

### 1. Criar e ativar o ambiente virtual (PowerShell)

Na raiz do repositório:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar dependências

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements-m5-groq.txt
```

O adaptador Gemini é opcional. Para instalá-lo também:

```powershell
python -m pip install -r requirements-m5.txt
```

### 3. Preparar os dados privados

Crie a pasta local:

```powershell
New-Item -ItemType Directory -Force data\private\source | Out-Null
```

Copie para `data/private/source/` os CSVs originais, renomeados exatamente assim:

```text
data/private/source/products.csv
data/private/source/categories.csv
data/private/source/promotions.csv
data/private/source/customers.csv
data/private/source/orders.csv
data/private/source/order_items.csv
```

Copie o manual fornecido para:

```text
data/private/store_policies.pdf
```

O PDF é um manual interno marcado como restrito. **Não o publique no GitHub.** Também não publique os CSVs, especialmente os dados de clientes e pedidos.

### 4. Configurar o provedor

Crie uma chave em [GroqCloud](https://console.groq.com/keys). Abra `.env` na raiz do repositório e configure:

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=sua_chave_groq
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1

DATA_SOURCE_DIR=data/private/source
POLICY_PDF_PATH=data/private/store_policies.pdf
DATABASE_PATH=data/private/emporio.sqlite3
```

Não adicione aspas à chave, não a compartilhe e não faça commit do `.env`.

Para usar Gemini em vez de Groq, configure `LLM_PROVIDER=gemini`, `GEMINI_API_KEY` e `GEMINI_MODEL`. A dependência correspondente é instalada com `requirements-m5.txt`.

### 5. Verificar e executar

Auditar/carregar os dados:

```powershell
python -m app.data
```

Executar a avaliação de recuperação do manual:

```powershell
python -m app.knowledge
```

Iniciar o atendimento:

```powershell
python -m app.agent
```

Digite `sair` para encerrar a conversa.

## Testes

A suíte completa pode ser executada sem chave de API:

```powershell
python -m pytest -q
```

Os testes unitários usam serviços/clientes simulados. Os testes de integração e avaliação usam os CSVs e o PDF locais do desafio. Os adaptadores LLM usam clientes simulados na suíte; uma conversa real com o provedor exige uma chave e disponibilidade da API.

Na validação do pacote após M5.2, a suíte completa executou com **103 testes aprovados** em Python 3.13.5. Repita o comando acima no ambiente em que o repositório será entregue.

## Exemplos de interação

O arquivo [`examples/M5_CONVERSATIONS.md`](examples/M5_CONVERSATIONS.md) contém quatro cenários: busca de catálogo, detalhes de produto, política de arrependimento e conflito de garantia que exige revisão humana. Os exemplos distinguem informações do snapshot das regras do manual.

## Segurança e privacidade

- O `.env`, `data/private/`, bancos SQLite locais e artefatos de dados privados devem permanecer fora do Git.
- A consulta de pedido é feita em duas etapas. O modelo solicita somente o ID do pedido; o telefone é capturado e validado localmente pela aplicação, sem ser anexado ao histórico enviado ao provedor.
- Telefones reconhecidos em mensagens comuns são mascarados antes de entrar no histórico do modelo.
- As mensagens necessárias à resposta, o prompt, as declarações de ferramentas e resultados de ferramentas podem ser enviados ao provedor LLM configurado. Não use dados reais de clientes em uma demonstração pública sem revisão de privacidade, segurança, retenção e base legal.
- O protótipo não usa CRM, não abre chamados e não notifica funcionários. Quando necessário, apenas informa que o caso deve ser confirmado pela equipe.

## Limitações conhecidas e próximos passos possíveis

- CLI apenas; não há interface web, WhatsApp, streaming ou API HTTP.
- Estoque, promoções e pedidos são snapshots estáticos.
- Histórico não persiste entre execuções.
- Não existe checkout, pagamento real, CRM, sistema de tickets ou fila de atendimento humano.
- O manual recebido é versão 2.1, de junho de 2025, e pode não refletir políticas posteriores.
- Alguns pontos do manual seguem sem resolução: garantia após 30 dias, frete exatamente em R$ 500, canais de contato e interpretação de mínimos de parcelamento. Casos marcados como conflitantes são encaminhados para confirmação humana; a regra detalhada da seção 3.1 para parcelamento foi adotada e documentada.
- A qualidade do texto final ainda depende do modelo. A aplicação passou a formatar os detalhes de produto de maneira determinística para evitar reinterpretação incorreta de campos técnicos, mas outras respostas devem continuar sendo monitoradas.
- Em produção, seriam necessários observabilidade, limites de requisição, gestão de segredos, TLS, controle de acesso, política formal de retenção, monitoramento de custo/latência e revisão periódica da base de políticas.

## Uso de assistentes de código

ChatGPT (OpenAI) foi utilizado como assistente de desenvolvimento ao longo do projeto para discutir arquitetura, decompor o trabalho em marcos, elaborar e revisar código, sugerir testes, investigar erros de integração e preparar documentação. O uso foi iterativo: as alterações eram aplicadas ao repositório, executadas localmente e verificadas com testes automatizados e testes manuais no terminal. O desenvolvedor decidiu as integrações, executou os comandos, avaliou os resultados e validou o comportamento final. Não foi usado um agente autônomo para publicar commits.

## Estrutura de referência

```text
app/
  agent/       # prompt, sessão, segurança e runtime
  data/        # SQLite, CSV loader e repositories
  domain/      # modelos, schemas, enums e erros
  knowledge/  # extração, chunking, BM25, conflitos e avaliação
  llm/         # contratos e adaptadores de provedores
  services/    # regras de negócio
  tools/       # registry e ferramentas do agente
examples/      # conversas demonstrativas
 tests/        # unit, integration e evaluations
 data/private/ # arquivos locais; nunca versionar
```

---

Projeto desenvolvido para o desafio técnico de AI Engineer — Artefact. A Empório da Música é fictícia e as informações operacionais refletem exclusivamente os arquivos fornecidos para o desafio.
