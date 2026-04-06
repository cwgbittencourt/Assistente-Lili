# Lili

Assistente local com ativacao por texto, comando de voz e resposta falada.

## Requisitos
1. Windows 10/11.
2. Python 3.11.
3. Microfone configurado no sistema.

## Instalacao
1. Crie e ative um ambiente virtual.
```powershell
py -3.11 -m venv Lili\.venv
.\Lili\.venv\Scripts\Activate.ps1
```
2. Instale as dependencias.
```powershell
pip install -r requirements.txt
```
3. Se voce alterar dependencias, gere novamente o arquivo:
```powershell
.\Lili\.venv\Scripts\Activate.ps1
pip freeze > requirements.txt
```
3. Copie o arquivo de configuracao.
```powershell
Copy-Item Lili\.env.example Lili\.env
```

## Execucao
```powershell
.\Lili\.venv\Scripts\Activate.ps1
python Lili\run.py
```

## Configuracao
O arquivo `Lili/.env` controla os parametros principais. Os mais usados:
1. `WAKEWORD_PHRASES` lista separada por virgula que dispara a ativacao (ex.: `computador,assistente`).
2. `WAKEWORD_FALLBACK_MODEL` modelo Whisper usado para detectar a palavra de ativacao via STT (ex.: `tiny`, `small`).
3. `INPUT_DEVICE_INDEX` indice do microfone. Deixe vazio para o padrao.
4. `STT_PROVIDER` `faster_whisper`, `openai_whisper` ou `mock`.
5. `CHAT_PROVIDER` `mock` ou `ollama` (usa `CHAT_BASE_URL` e `CHAT_MODEL`).
6. `TTS_PROVIDER` `pyttsx3`.

## Como funciona
1. O microfone roda em modo continuo.
2. A ativacao usa o STT para transcrever pequenos trechos de voz.
3. Se o texto transcrito contiver uma das frases de `WAKEWORD_PHRASES`, a ativacao dispara.
4. Em seguida a app captura o comando completo, transcreve, envia ao chat e fala a resposta.

## Estrutura do projeto
1. `Lili/app` codigo principal (servicos, audio, UI, STT, TTS).
2. `Lili/app/wakeword` ativacao por STT (detecao da frase).
3. `Lili/app/audio` captura de audio e VAD.
4. `Lili/app/ui` interface principal.
5. `Lili/tests` testes de unidade.
6. `Lili/models` modelos baixados (nao versionar no git).

## Ativacao por texto

A ativacao acontece pela comparacao do texto transcrito com uma lista de frases.
Nao ha modelo ONNX de wake word no pipeline atual; a deteccao usa STT.
Edite a lista no arquivo `Lili/.env` com a chave `WAKEWORD_PHRASES` ou use a interface.

## Modelos
1. O `faster_whisper` baixa modelos automaticamente no primeiro uso.
2. O `openai_whisper` baixa em `Lili/models/whisper` (configuravel por `STT_MODEL_DOWNLOAD_ROOT`).

## Solucao de problemas
1. Se nao ativa, verifique a transcricao exibida na UI e ajuste `WAKEWORD_PHRASES`.
2. Para melhorar a detecao, use `WAKEWORD_FALLBACK_MODEL=small` e `WAKEWORD_FALLBACK_BEAM_SIZE=3`.
3. Se o microfone nao aparece, ajuste `INPUT_DEVICE_INDEX` conforme o log de inicializacao.

## Como contribuir
Este projeto esta funcional, mas nao pretendo evolui-lo. Sinta-se a vontade para fazer um fork e desenvolver novas ideias, por exemplo:
1. adicionar memória nas conversas;
2. implementar wake word dedicado (ex.: ONNX);
3. conectar agentes ou ferramentas externas.
