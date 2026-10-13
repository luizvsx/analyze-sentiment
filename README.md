# Análise de sentimentos de comentários

Projeto desenvolvido acompanhando um curso, com ajustes próprios de validação, tratamento de erros, modo mock e documentação.

Aplicação em Python que recebe comentários e avaliações de 1 a 5 estrelas, analisa o conteúdo com o Gemini e salva os resultados no MongoDB. A análise considera a coerência entre comentário e nota e a presença de conteúdo agressivo ou discriminatório.

## Como funciona

1. O usuário envia um comentário pelo Streamlit.
2. O FastAPI valida os dados e envia uma mensagem ao tópico `feedback` do Kafka.
3. O consumidor consulta o Gemini e salva o resultado no MongoDB.
4. O consumidor confirma a mensagem após salvar o resultado.
5. O usuário consulta os resultados na aba **Feedbacks salvos**, usando **Atualizar lista**.

O envio confirma a entrada na fila; a análise acontece depois. Falhas temporárias de conexão, limite de requisições e determinados erros do Gemini recebem novas tentativas. Se persistirem, o consumidor retoma após 60 segundos sem confirmar a mensagem. Outras falhas interrompem o consumidor. Uma interrupção entre a gravação e a confirmação pode gerar registros duplicados.

## Estrutura

```text
app/
├── backend/
│   ├── api_client.py       # Integração com o Gemini e modo mock
│   ├── config.py           # Configurações de ambiente
│   ├── fast_api.py         # Rotas HTTP
│   ├── kafka_consumer.py   # Processamento e persistência
│   ├── kafka_producer.py   # Envio de mensagens
│   └── mongodb.py          # Conexão com o banco
├── frontend/
│   └── streamlit.py        # Interface
├── .env.example
├── docker-compose.yml
├── main.py                # Inicialização local dos processos
└── requirements.txt       # Dependências para execução local
```

## Configuração

Após clonar este repositório, entre na pasta `app` e configure o ambiente:

```bash
cd analyze-sentiment/app
cp .env.example .env
```

O exemplo inicia em modo mock, sem precisar de uma chave ou fazer chamadas ao Gemini. Ele retorna uma resposta fixa com status `aprovado`, apenas para testar o fluxo; não realiza análise de sentimento.

Para usar o Gemini, edite o `.env` na pasta `app`:

```dotenv
GEMINI_API_KEY=sua_chave_aqui
MOCK_GEMINI_SERVICE=false
```

O modelo configurado no código é `gemini-3.1-flash-lite`. Seu uso exige acesso ao modelo na conta utilizada. Não publique o arquivo `.env`.

Configurações adicionais:

| Variável | Padrão local | Finalidade |
| --- | --- | --- |
| `MONGODB_URI` | `mongodb://localhost:27017/` | Endereço do MongoDB |
| `MONGODB_DATABASE` | `local` | Banco para a coleção `feedback` |
| `KAFKA_BROKER` | `localhost:9092` | Endereço do Kafka |
| `FASTAPI_HOST` | `fastapi` | Host usado pelo frontend; em execução local, use `localhost` |

O Compose define os endereços internos do Kafka, MongoDB e FastAPI. A variável `MONGO_URI`, quando definida, tem prioridade sobre `MONGODB_URI`.

## Executar com Docker

Requisitos: Docker Engine e Docker Compose.

```bash
docker compose up --build -d
```

O FastAPI e o consumidor aguardam o Kafka passar na verificação de saúde. A inicialização pode levar alguns minutos.

- Interface: http://localhost:8501
- Documentação da API: http://localhost:8000/docs
- Interface de inspeção do Kafka (Kowl): http://localhost:8080

Para acompanhar e encerrar:

```bash
docker compose logs -f fastapi consumer
docker compose down
```

O MongoDB usa o volume `mongodb-data` para manter os registros ao recriar contêineres. `docker compose down -v` remove esse volume e apaga os dados.

## Executar localmente

Requisitos: Python 3.11 ou superior, com suporte a `venv`, e Docker Compose para Kafka e MongoDB.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
docker compose up -d zookeeper kafka mongodb
```

No Windows, ative o ambiente com `.venv\Scripts\activate`. Aguarde o Kafka ficar saudável, conferindo `docker compose ps`, antes de iniciar a aplicação.

```bash
python main.py
```

Esse comando inicia o frontend, o consumidor e o FastAPI. Para executar em terminais separados, com o ambiente virtual ativo e a pasta `app` como diretório atual:

```bash
# Terminal 1: API
python -m uvicorn fast_api:app --app-dir backend --host 0.0.0.0 --port 8000

# Terminal 2: consumidor
python backend/kafka_consumer.py

# Terminal 3: frontend (Linux/macOS)
FASTAPI_HOST=localhost python -m streamlit run frontend/streamlit.py
```

Ao executar o frontend no Windows, defina `FASTAPI_HOST=localhost` usando a sintaxe do seu terminal. No iniciador `main.py`, se algum subprocesso permanecer ativo após encerrar a API, encerre-o também.

## API

- `POST /feedback/`: recebe `comment` (1 a 5.000 caracteres, sem aceitar apenas espaços) e `rating` (1 a 5). Retorna a confirmação de envio à fila. Dados inválidos retornam HTTP 422; falha de entrega retorna HTTP 503.
- `GET /feedback/`: lista até 100 resultados, dos mais recentes aos mais antigos.
- `GET /feedback/{comment}`: consulta um resultado pelo texto exato do comentário. Retorna HTTP 404 se não existir. Caracteres especiais precisam ser codificados na URL; comentários com barras devem ser consultados pela listagem.

Exemplo de envio:

```bash
curl -X POST http://localhost:8000/feedback/ \
  -H 'Content-Type: application/json' \
  -d '{"comment": "Gostei muito do produto!", "rating": 5}'
```

## Testes

Dentro da pasta `app`, com o ambiente virtual ativo:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Os testes verificam envio e validação de comentários, falha de entrega ao Kafka, consulta de feedback e modo mock. Kafka, MongoDB e Gemini são substituídos nos testes; não é necessário iniciar os serviços.

## Aprendizados

- Separação de interface e API com Streamlit e FastAPI.
- Processamento assíncrono com Kafka e confirmação manual no consumidor.
- Persistência de documentos com MongoDB.
- Integração com um modelo de IA e tratamento de falhas temporárias.
- Execução de serviços com Docker Compose e testes isolados.

## Limitações do projeto de estudo

Não há autenticação, paginação além do limite de 100 resultados, prevenção de duplicatas ou recuperação automática de todas as falhas do consumidor. As dependências diretas estão fixadas nas versões presentes no ambiente consultado; dependências transitivas não têm lockfile. Os serviços devem ser usados em um ambiente de desenvolvimento controlado.
