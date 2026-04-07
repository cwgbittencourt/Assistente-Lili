# Lili

Assistente local com ativacao por texto, comando de voz e resposta falada.

## Requisitos

1. Windows 10 ou Windows 11
2. Python 3.11
3. Microfone configurado no sistema
4. GPU NVIDIA compatível com CUDA 12.4 (**recomendada para uma boa experiência**)

> Observação:
> O projeto está configurado atualmente com `torch==2.4.1+cu124`.
> Se você não tiver GPU NVIDIA compatível com CUDA 12.4, será necessário ajustar a dependência do PyTorch para uma variante compatível com CPU ou com o seu ambiente.

## Instalacao
> **Atenção:** abra o terminal na pasta raiz do projeto, isto é, a pasta **`Lili`**, onde está o arquivo `requirements.txt`. Se você executar os comandos em outra pasta, a instalação poderá falhar.

Na **pasta raiz do repositório**, execute:

```powershell
py -3.11 -m venv .\Lili\.venv
.\Lili\.venv\Scripts\python.exe -m pip install --upgrade pip
.\Lili\.venv\Scripts\python.exe -m pip install torch==2.4.1+cu124 --index-url https://download.pytorch.org/whl/cu124
.\Lili\.venv\Scripts\python.exe -m pip install -r .\Lili\requirements.txt --extra-index-url https://download.pytorch.org/whl/cu124
Copy-Item .\Lili\.env.example .\Lili\.env -Force
```

## Execucao
```powershell
.\Lili\.venv\Scripts\python.exe .\Lili\run.py
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
