from app.core import AppState, AppStateMachine


def test_state_machine_accepts_valid_transition_and_emits_signal() -> None:
    machine = AppStateMachine()
    transitions: list[tuple[AppState, AppState]] = []
    machine.state_changed.connect(lambda previous, new: transitions.append((previous, new)))

    assert machine.transition_to(AppState.AGUARDANDO_WAKE_WORD) is True
    assert machine.current_state == AppState.AGUARDANDO_WAKE_WORD
    assert transitions == [(AppState.INICIALIZANDO, AppState.AGUARDANDO_WAKE_WORD)]


def test_state_machine_rejects_invalid_transition() -> None:
    machine = AppStateMachine(initial_state=AppState.AGUARDANDO_WAKE_WORD)

    assert machine.transition_to(AppState.REPRODUZINDO_RESPOSTA) is False
    assert machine.current_state == AppState.AGUARDANDO_WAKE_WORD
