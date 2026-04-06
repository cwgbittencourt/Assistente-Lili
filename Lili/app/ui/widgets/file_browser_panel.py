from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDir, Qt
from PySide6.QtWidgets import (
    QFileSystemModel,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QTreeView,
    QVBoxLayout,
)


class FileBrowserPanel(QGroupBox):
    def __init__(self, project_root: Path) -> None:
        super().__init__("Arquivos do projeto")
        self._project_root = project_root.resolve()
        self._preview_limit_bytes = 128 * 1024

        self._file_model = QFileSystemModel(self)
        self._file_model.setRootPath(str(self._project_root))
        self._file_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)

        self._tree = QTreeView(self)
        self._tree.setModel(self._file_model)
        self._tree.setRootIndex(self._file_model.index(str(self._project_root)))
        self._tree.setHeaderHidden(True)
        self._tree.setAnimated(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.setColumnHidden(1, True)
        self._tree.setColumnHidden(2, True)
        self._tree.setColumnHidden(3, True)
        self._tree.clicked.connect(self._handle_item_selected)

        self._path_label = QLabel(f"Raiz: {self._project_root}")
        self._path_label.setWordWrap(True)
        self._path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self._preview = QPlainTextEdit(self)
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText("Selecione um arquivo para visualizar o conteudo.")

        content_layout = QHBoxLayout()
        content_layout.addWidget(self._tree, 2)
        content_layout.addWidget(self._preview, 3)

        layout = QVBoxLayout(self)
        layout.addWidget(self._path_label)
        layout.addLayout(content_layout)

    def _handle_item_selected(self, index) -> None:
        file_path = Path(self._file_model.filePath(index))
        self._path_label.setText(f"Selecionado: {file_path}")

        if file_path.is_dir():
            self._preview.setPlainText(f"Pasta selecionada:\n{file_path}")
            return

        self._preview.setPlainText(self._read_preview(file_path))

    def _read_preview(self, file_path: Path) -> str:
        try:
            size = file_path.stat().st_size
        except OSError as exc:
            return f"Nao foi possivel acessar o arquivo.\n{exc}"

        if size > self._preview_limit_bytes:
            return (
                "Arquivo grande demais para pre-visualizacao.\n"
                f"Tamanho: {size} bytes.\n"
                f"Limite atual: {self._preview_limit_bytes} bytes."
            )

        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return "Arquivo binario ou com codificacao nao suportada para visualizacao."
        except OSError as exc:
            return f"Nao foi possivel ler o arquivo.\n{exc}"
