"""Consistent Chinese application dialogs."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox, QWidget


def ask_confirmation(
    parent: QWidget | None,
    title: str,
    text: str,
    confirm_text: str = "确认",
    cancel_text: str = "取消",
    destructive: bool = False,
) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(text)
    confirm = box.addButton(confirm_text, QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton(cancel_text, QMessageBox.ButtonRole.RejectRole)
    confirm.setObjectName("dangerButton" if destructive else "primaryButton")
    cancel.setObjectName("ghostButton")
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    box.exec()
    return box.clickedButton() is confirm


def show_information(parent: QWidget | None, title: str, text: str):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(title)
    box.setText(text)
    done = box.addButton("知道了", QMessageBox.ButtonRole.AcceptRole)
    done.setObjectName("primaryButton")
    box.setDefaultButton(done)
    box.exec()


def show_critical(parent: QWidget | None, title: str, text: str):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title)
    box.setText(text)
    done = box.addButton("关闭", QMessageBox.ButtonRole.AcceptRole)
    done.setObjectName("primaryButton")
    box.setDefaultButton(done)
    box.exec()

