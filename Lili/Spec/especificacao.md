# Lili — Guia Prático para Implementação com Codex no Visual Studio 2026

## Objetivo

Implementar uma aplicação desktop em Python que:

- fique escutando continuamente o microfone
- detecte a wake word **Lili** via STT (fallback)
- após a ativação, capture o comando falado
- transcreva o áudio em texto
- envie o texto para um chat de IA
- receba a resposta em texto
- fale a resposta com TTS
- exiba gráficos/animações de áudio na interface

Este documento foi escrito para uso direto com Codex/Copilot no Visual Studio 2026, com foco em implementação prática por etapas.

## Status atual (2026-04-06)

- O pipeline atual usa STT para detectar a wake word.
- Modelos ONNX de wake word nao sao utilizados.
- A pasta `models/` e usada apenas para modelos Whisper quando aplicavel.

---

## Regra principal para o agente de código

Implemente em **fases pequenas, executáveis e testáveis**.

Não tente entregar tudo de uma vez.

Cada fase deve:
1. compilar/rodar
2. ter estrutura limpa
3. preparar a próxima fase
4. deixar logs claros
5. evitar acoplamento forte

---

## Stack recomendada

- Python 3.11+
- PySide6
- sounddevice
- numpy
- pyttsx3
- requests ou httpx
- logging padrão do Python

Opcional depois:
- Faster-Whisper (ja utilizado no wakeword por STT)
- integração com Ollama
- VAD mais refinado

---

## Estrutura de pastas desejada

```text
lili_assistente/
├─ app/
│  ├─ main.py
│  ├─ bootstrap.py
│  ├─ config.py
│  ├─ constants.py
│  │
│  ├─ core/
│  │  ├─ state_machine.py
│  │  ├─ models.py
│  │  ├─ logger.py
│  │  └─ exceptions.py
│  │
│  ├─ audio/
│  │  ├─ input_stream.py
│  │  ├─ output_stream.py
│  │  ├─ audio_buffer.py
│  │  ├─ vad.py
│  │  └─ level_meter.py
│  │
│  ├─ wakeword/
│  │  └─ wakeword_stt_service.py
│  │
│  ├─ stt/
│  │  ├─ base.py
│  │  ├─ mock_stt.py
│  │  └─ stt_service.py
│  │
│  ├─ ai/
│  │  ├─ base.py
│  │  ├─ mock_chat.py
│  │  ├─ ollama_client.py
│  │  └─ chat_service.py
│  │
│  ├─ tts/
│  │  ├─ base.py
│  │  ├─ pyttsx3_engine.py
│  │  └─ tts_service.py
│  │
│  ├─ ui/
│  │  ├─ main_window.py
│  │  ├─ app_viewmodel.py
│  │  └─ widgets/
│  │     ├─ status_panel.py
│  │     ├─ waveform_widget.py
│  │     ├─ level_meter_widget.py
│  │     ├─ transcript_panel.py
│  │     └─ response_panel.py
│  │
│  └─ services/
│     ├─ command_capture_service.py
│     └─ orchestration_service.py
│
├─ doc/
│  └─ Lili_Codex_Implementacao_Pratico.md
│
├─ tests/
├─ requirements.txt
├─ .env.example
└─ run.py
```

---

## Ordem obrigatória de implementação

## Fase 1 — Criar a base do projeto

### Objetivo
Montar a estrutura inicial do projeto e abrir a janela principal.

### O que o Codex deve fazer
1. Criar a árvore de pastas.
2. Criar `requirements.txt`.
3. Criar `app/main.py` e `run.py`.
4. Criar `app/config.py`.
5. Criar `app/core/logger.py`.
6. Criar uma janela PySide6 simples.
7. Exibir status inicial: **Aguardando Lili...**

### Critério de aceite
- A aplicação abre sem erro.
- A janela aparece.
- O log informa inicialização com sucesso.

### Prompt prático para o Codex
```text
Crie a estrutura inicial de uma aplicação desktop em Python com PySide6.
Implemente:
- run.py
- app/main.py
- app/config.py
- app/core/logger.py
- app/ui/main_window.py

A aplicação deve abrir uma janela principal com:
- título "Lili"
- um label de status com o texto "Aguardando Lili..."
- área reservada para gráficos de áudio
- área reservada para texto do usuário
- área reservada para resposta da IA

Use tipagem, logging e organização limpa.
Não implemente ainda wake word, STT ou IA. Apenas a base executável.
```

---

## Fase 2 — Captura contínua do microfone

### Objetivo
Ler o microfone continuamente sem travar a interface.

### O que o Codex deve fazer
1. Criar `app/audio/input_stream.py`.
2. Implementar captura contínua com `sounddevice`.
3. Criar cálculo simples de nível de áudio.
4. Atualizar a UI em tempo real com esse nível.
5. Exibir um medidor visual simples.

### Regras
- Não bloquear a thread principal.
- Usar worker/thread ou sinais do Qt.
- O stream deve poder iniciar e parar com segurança.

### Critério de aceite
- O microfone é lido continuamente.
- O medidor responde à fala.
- A UI não congela.

### Prompt prático para o Codex
```text
Implemente a captura contínua do microfone em uma aplicação PySide6 usando sounddevice.

Crie:
- app/audio/input_stream.py
- app/audio/level_meter.py
- integração com app/ui/main_window.py

Requisitos:
- capturar áudio continuamente
- calcular nível RMS ou amplitude média
- atualizar a interface em tempo real
- mostrar um medidor visual simples
- não travar a UI
- usar sinais/slots ou mecanismo thread-safe

Ainda não implemente wake word. Apenas captação contínua e feedback visual.
```

---

## Fase 3 — Widget visual de áudio

### Objetivo
Deixar a interface mais próxima do comportamento esperado, com gráfico reativo.

### O que o Codex deve fazer
1. Criar `waveform_widget.py`.
2. Exibir uma forma de onda simplificada ou barras verticais.
3. Alimentar o widget com os chunks recentes do áudio.

### Critério de aceite
- A área gráfica reage ao som da voz.
- A atualização é suave.
- O widget é reaproveitável.

### Prompt prático para o Codex
```text
Crie um widget PySide6 reutilizável chamado WaveformWidget.
Ele deve desenhar uma visualização simples do áudio do microfone em tempo real.

Requisitos:
- aceitar atualização de amostras ou níveis
- desenhar waveform simplificada ou barras verticais
- ter boa performance
- integrar com a captura de áudio já implementada
- não usar lógica de negócio dentro do widget
```

---

## Fase 5 — Máquina de estados da aplicação

### Objetivo
Controlar o ciclo do assistente de forma limpa.

### Estados mínimos
- `INICIALIZANDO`
- `AGUARDANDO_WAKE_WORD`
- `WAKE_WORD_DETECTADA`
- `CAPTURANDO_COMANDO`
- `TRANSCREVENDO`
- `ENVIANDO_PARA_IA`
- `REPRODUZINDO_RESPOSTA`
- `ERRO`

### O que o Codex deve fazer
1. Criar `app/core/state_machine.py`.
2. Modelar estados e transições válidas.
3. Expor eventos para a UI reagir.

### Critério de aceite
- Os estados ficam centralizados.
- A UI reflete o estado atual.
- O fluxo fica mais fácil de manter.

### Prompt prático para o Codex
```text
Implemente uma máquina de estados simples para a aplicação Lili.

Crie:
- app/core/state_machine.py

Requisitos:
- definir enum de estados
- permitir transições controladas
- registrar transições no log
- expor estado atual para a UI
- facilitar integração posterior com wake word, STT, IA e TTS
```

---

## Fase 7 — Captura do comando após wake word

### Objetivo
Depois da palavra de ativação, gravar o que o usuário falar até detectar silêncio.

### O que o Codex deve fazer
1. Criar `command_capture_service.py`.
2. Iniciar buffer do comando após a wake word.
3. Detectar silêncio por energia.
4. Encerrar a gravação após alguns milissegundos de silêncio contínuo.
5. Impor limite máximo de duração.

### Critério de aceite
- O usuário fala uma frase.
- O sistema grava a frase inteira.
- Após silêncio, segue para transcrição.

### Prompt prático para o Codex
```text
Implemente a captura do comando de voz após a detecção da wake word.

Crie:
- app/services/command_capture_service.py
- app/audio/vad.py

Requisitos:
- iniciar captura após evento de wake word
- acumular o áudio do comando
- encerrar por silêncio contínuo
- ter duração máxima configurável
- descartar capturas vazias
- integrar com a máquina de estados
```

---

## Fase 8 — STT com implementação mock primeiro

### Objetivo
Ligar o pipeline sem depender inicialmente de um transcritor real.

### O que o Codex deve fazercodex
1. Criar interface base de STT.
2. Criar `mock_stt.py`.
3. Fazer o mock retornar texto fixo de teste.
4. Exibir esse texto na UI.

### Critério de aceite
- O pipeline completo vai da wake word até texto na tela.
- Mesmo sem STT real, o fluxo é validado.

### Prompt prático para o Codex
```text
Implemente a camada de STT da aplicação com interface e mock inicial.

Crie:
- app/stt/base.py
- app/stt/mock_stt.py
- app/stt/stt_service.py

Requisitos:s
- definir contrato de transcrição
- criar resultado estruturado
- mockar um texto fixo para validar o fluxo
- integrar com a máquina de estados e a UI

Ainda não usar modelo real de transcrição.
```

---

## Fase 9 — Chat IA com mock e depois adapter real

### Objetivo
Validar a orquestração antes do backend real.

### O que o Codex deve fazer
1. Criar interface de chat.
2. Criar `mock_chat.py`.
3. Integrar com o pipeline.
4. Depois criar `ollama_client.py` por adapter.

### Critério de aceite
- O texto do usuário gera uma resposta mock.
- A resposta aparece na tela.
- O fluxo já fica pronto para backend real.

### Prompt prático para o Codex
```text
Implemente a camada de chat IA com interface e mock inicial.

Crie:
- app/ai/base.py
- app/ai/mock_chat.py
- app/ai/chat_service.py

Requisitos:
- definir contrato para envio de pergunta
- retornar resposta estruturada
- integrar com o fluxo da aplicação
- exibir a resposta na UI
- preparar a arquitetura para provider real depois
```

### Prompt adicional para provider real com Ollama
```text
Agora implemente um adapter real para Ollama compatível com a camada de chat existente.

Crie:
- app/ai/ollama_client.py

Requisitos:
- usar endpoint configurável
- usar modelo configurável
- tratar timeout
- tratar falhas HTTP
- retornar resposta estruturada
- não acoplar a UI ao provider
```

---

## Fase 10 — TTS com `pyttsx3`

### Objetivo
Fazer a resposta falar.

### O que o Codex deve fazer
1. Criar interface de TTS.
2. Criar provider com `pyttsx3`.
3. Integrar ao pipeline.
4. Atualizar estado para `REPRODUZINDO_RESPOSTA`.

### Critério de aceite
- O texto da resposta é falado.
- Ao terminar, volta para modo de espera.

### Prompt prático para o Codex
```text
Implemente a camada de TTS com pyttsx3.

Crie:
- app/tts/base.py
- app/tts/pyttsx3_engine.py
- app/tts/tts_service.py

Requisitos:
- falar o texto recebido
- não travar a UI
- informar início e fim da reprodução
- integrar com máquina de estados
- ao terminar, retornar a aplicação para AGUARDANDO_WAKE_WORD
```

---

## Fase 11 — Orquestração central

### Objetivo
Centralizar o fluxo fim a fim.

### O que o Codex deve fazer
Criar `orchestration_service.py` para coordenar:

- wake word
- captura do comando
- STT
- chat
- TTS
- atualização de estado
- atualização da UI

### Critério de aceite
- O pipeline completo fica centralizado.
- Os módulos ficam desacoplados.

### Prompt prático para o Codex
```text
Crie um serviço central de orquestração para a aplicação Lili.

Crie:
- app/services/orchestration_service.py

Responsabilidades:
- reagir ao evento de wake word detectada
- iniciar captura do comando
- enviar áudio ao STT
- enviar texto ao chat
- enviar resposta ao TTS
- atualizar a máquina de estados
- notificar a UI

O objetivo é manter a UI limpa e concentrar o fluxo em um único serviço coordenador.
```

---

## Fase 12 — Melhorias visuais e UX

### Objetivo
Aproximar a aplicação do comportamento final.

### Melhorias esperadas
- status visual mais claro
- área “Você disse”
- área “Lili respondeu”
- gráfico mais bonito
- indicador de processamento
- indicador de fala da IA
- botão futuro de parar voz

### Prompt prático para o Codex
```text
Refatore a interface da aplicação Lili para ficar mais clara e moderna.

Implemente:
- painel de status
- painel do texto do usuário
- painel da resposta da IA
- indicador visual de processamento
- visualização de áudio mais agradável

Requisitos:
- manter separação entre UI e lógica de negócio
- usar widgets reutilizáveis
- não quebrar a arquitetura já implementada
```

---

## Fase 13 — Configuração externa

### Objetivo
Permitir ajustes sem editar código.

### Arquivo `.env.example` sugerido

```env
APP_NAME=Lili
DEBUG=true

INPUT_DEVICE_INDEX=
OUTPUT_DEVICE_INDEX=

AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
AUDIO_BLOCKSIZE=1024

WAKEWORD_PHRASES=lili,jarvis
WAKEWORD_FALLBACK_MODEL=tiny
WAKEWORD_FALLBACK_BEAM_SIZE=1
WAKEWORD_FALLBACK_VAD_THRESHOLD=0.02
WAKEWORD_FALLBACK_MIN_DURATION_MS=300
WAKEWORD_FALLBACK_MAX_DURATION_MS=1200
WAKEWORD_FALLBACK_SILENCE_TIMEOUT_MS=400
WAKEWORD_FALLBACK_COOLDOWN_MS=1500

COMMAND_SILENCE_TIMEOUT_MS=1800
COMMAND_MAX_DURATION_MS=10000
COMMAND_MIN_DURATION_MS=500

CHAT_PROVIDER=ollama
CHAT_BASE_URL=http://localhost:11434
CHAT_MODEL=qwen2.5:7b-instruct
CHAT_TIMEOUT_SECONDS=60

TTS_PROVIDER=pyttsx3
TTS_RATE=180
TTS_VOLUME=1.0

LOG_LEVEL=INFO
```

### Prompt prático para o Codex
```text
Adicione suporte a configuração externa via .env para a aplicação Lili.

Requisitos:
- centralizar a leitura de configuração
- permitir configurar áudio, wake word, chat, TTS e logs
- fornecer .env.example
- evitar valores mágicos espalhados pelo código
```

---

## Fase 14 — Testes mínimos

### O que o Codex deve testar
- máquina de estados
- leitura da configuração
- cooldown da wake word
- VAD simples
- mocks de STT e chat

### Prompt prático para o Codex
```text
Crie testes unitários mínimos para a aplicação Lili.

Prioridades:
- state machine
- configuração
- cooldown da wake word
- lógica simples de silêncio/VAD
- mocks de STT e chat

Use pytest e mantenha os testes pequenos e claros.
```

---

## Regras de arquitetura que o Codex deve respeitar

1. Não colocar regra de negócio dentro de widget Qt.
2. Não acoplar diretamente a UI ao provider de IA.
3. Não acoplar diretamente a UI ao backend de STT.
4. Não bloquear a UI com inferência, HTTP, STT ou TTS.
5. Criar contratos claros para STT, chat e TTS.
6. Usar logs em pontos importantes.
7. Escrever código com tipagem.
8. Preferir classes pequenas e focadas.
9. Preparar o projeto para troca futura de backend.
10. Entregar cada fase rodando antes de seguir para a próxima.

---

## Ordem recomendada de execução no Visual Studio 2026 com Codex

1. Pedir para criar a base do projeto.
2. Rodar.
3. Pedir captura de microfone.
4. Rodar.
5. Pedir widget visual.
6. Rodar.
7. Pedir wake word via STT (fallback).
8. Rodar.
9. Pedir captura do comando.
10. Rodar.
11. Pedir STT mock.
12. Rodar.
13. Pedir chat mock.
14. Rodar.
15. Pedir TTS.
16. Rodar.
17. Pedir adapter real de chat.
18. Refinar.

---

## Instrução final para colar no Codex

```text
Implemente esta aplicação em etapas pequenas e seguras.

Contexto:
Quero uma aplicação desktop em Python com PySide6 chamada Lili.
Ela deve:
- ouvir continuamente o microfone
- detectar a wake word "Lili" via STT (fallback)
- após a ativação, capturar o comando falado
- transcrever o comando
- enviar o texto para um chat de IA
- receber a resposta em texto
- falar a resposta com TTS
- mostrar feedback visual de áudio na tela

Regras:
- não implemente tudo de uma vez
- cada fase deve rodar antes da próxima
- use arquitetura modular
- não coloque regra de negócio na UI
- use tipagem
- use logging
- evite bloquear a thread principal

Comece pela fase 1:
crie a estrutura inicial do projeto, a janela principal em PySide6, logging, configuração e uma tela com status "Aguardando Lili...".
```

---

## Resultado esperado do MVP

O MVP estará correto quando:

1. a janela abrir normalmente
2. o microfone for lido continuamente
3. a tela mostrar gráfico/nível de áudio
4. a wake word for detectada
5. o comando for capturado até silêncio
6. o texto aparecer na tela
7. a IA responder em texto
8. a resposta for falada
9. o sistema voltar a esperar a palavra “Lili”
