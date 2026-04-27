from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLineEdit

from core.config import (
    log, static_password,
    DARK, LIGHT, D_CONF, R_CONF,
    BTN_DISABLE, SCALE_VIEW, SCALE_DISABLE, LOGIN_URL, UPLOAD_URL, USERNAME, PASSWORD, BASE_URL,
    default_username, default_password, default_det_conf, default_rec_conf,
    get_token_url, post_url,
    min_det_conf, max_det_conf, min_rec_conf, max_rec_conf,
)
from network.api import get_base_url
from threads.workers import LoginThread
from ui.settings_panel import (
    SpecialSettingsDialog, _get_view_icon, _get_unview_icon,
)
from utils.helpers import show_message


class PasswordSettingsMixin:

    def ask_password_window(self):
        try:
            self.apply_blur(enable=True)
            from ui.app import _PasswordPromptDialog
            self.password_dialog = _PasswordPromptDialog(style_name=self.style_name,
                                                          screen_width=self.screen_width,
                                                          screen_height=self.screen_height)
            self.password_dialog.enter_btn.clicked.connect(
                lambda: self.check_password(self.password_dialog.password.edit.text().strip()))
            self.password_dialog.password.edit.returnPressed.connect(
                lambda: self.check_password(self.password_dialog.password.edit.text().strip()))
            self.password_dialog.back_btn.clicked.connect(self.password_dialog.close)
            self.password_dialog.closeEvent = self._password_dialog_close
            self.password_dialog.exec()
        except (Exception, ValueError) as err:
            log(message=f"[App.ask_password_window] {err}")

    def _password_dialog_close(self, a0):
        if self.password_dialog.force_close:
            if self.password_dialog.isVisible():
                self.apply_blur(enable=False)
            a0.accept()
        else:
            a0.ignore()

    def check_password(self, txt: str):
        try:
            if txt == static_password:
                self.password_dialog.force_close = True
                self.password_dialog.close()
                self.apply_blur(enable=False)
                self.special_settings_dialog = SpecialSettingsDialog(
                    style_name=self.style_name,
                    screen_width=self.screen_width, screen_height=self.screen_height)
                self.apply_blur(enable=True)
                self.special_settings_dialog.closeEvent = self._close_hidden_settings_window
                self._populate_special_settings()
                self.special_settings_dialog.exec()
            else:
                self.password_dialog.force_close = False
                QTimer.singleShot(1_000, lambda: setattr(self.password_dialog, 'force_close', True))
                self.password_dialog.password.edit.setObjectName("wrong_password")
                self.password_dialog.password.edit.setStyleSheet(self.style_)
                QTimer.singleShot(2_000, self._clear_password_style)
        except (Exception, ValueError) as err:
            log(message=f"[App.check_password] {err}")

    def _clear_password_style(self):
        if self.password_dialog:
            self.password_dialog.password.edit.setObjectName("hidden1_settings_edit")
            self.password_dialog.password.edit.setStyleSheet(self.style_)

    def _close_hidden_settings_window(self, a0):
        self.apply_blur(enable=False)
        a0.accept()

    def _populate_special_settings(self):
        sd = self.special_settings_dialog
        sd.d_r_conf.col1.edit.setText(str(self.config.get(D_CONF, default_det_conf)))
        sd.d_r_conf.col2.edit.setText(str(self.config.get(R_CONF, default_rec_conf)))
        sd.urls.col1.edit.setText(str(self.config.get(LOGIN_URL, get_token_url)))
        sd.urls.col2.edit.setText(str(self.config.get(UPLOAD_URL, post_url)))
        sd.scale_view.hidden_switch.setChecked(self.config.get(SCALE_VIEW, False))
        sd.btn_disable.hidden_switch.setChecked(self.config.get(BTN_DISABLE, True))
        sd.scale_disable.hidden_switch.setChecked(self.config.get(SCALE_DISABLE, False))
        sd.login_widget.edit.setText(str(self.config.get(USERNAME, default_username)))
        sd.password_widget.edit.setText(str(self.config.get(PASSWORD, default_password)))
        sd.back_btn.clicked.connect(sd.close)
        sd.password_widget.password_toggle_btn.clicked.connect(self._toggle_password_edit)
        sd.login_widget.edit.setDisabled(False)
        sd.password_widget.edit.setDisabled(False)
        if self.last_login_status:
            sd.login_widget.lbl.setText("Login \u2705")
            sd.password_widget.lbl.setText("Parol \u2705")
        else:
            sd.login_widget.lbl.setText("Login \u274c")
            sd.password_widget.lbl.setText("Parol \u274c")
        sd.save_btn.clicked.connect(
            lambda: self.save_special_settings(data={
                BTN_DISABLE: sd.btn_disable.hidden_switch.isChecked(),
                SCALE_VIEW: sd.scale_view.hidden_switch.isChecked(),
                SCALE_DISABLE: sd.scale_disable.hidden_switch.isChecked(),
                LOGIN_URL: sd.urls.col1.edit.text().strip(),
                UPLOAD_URL: sd.urls.col2.edit.text().strip(),
                D_CONF: sd.d_r_conf.col1.edit.text().strip(),
                R_CONF: sd.d_r_conf.col2.edit.text().strip(),
                USERNAME: sd.login_widget.edit.text().strip(),
                PASSWORD: sd.password_widget.edit.text().strip(),
            })
        )

    def _toggle_password_edit(self):
        sd = self.special_settings_dialog
        if not isinstance(sd, SpecialSettingsDialog):
            return
        if sd.password_widget.edit.echoMode() == QLineEdit.EchoMode.Password:
            sd.password_widget.edit.setEchoMode(QLineEdit.EchoMode.Normal)
            ic = _get_unview_icon(dark=(self.style_name == DARK))
        else:
            sd.password_widget.edit.setEchoMode(QLineEdit.EchoMode.Password)
            ic = _get_view_icon(dark=(self.style_name == DARK))
        if ic:
            sd.password_widget.password_toggle_btn.setIcon(ic)

    def save_special_settings(self, data: dict):
        try:
            for key in [USERNAME, PASSWORD, LOGIN_URL, UPLOAD_URL]:
                if data.get(key, ""):
                    self.settings.patch(key=key, value=data[key])
                    self.config = self.settings.load()
            d_cnf = data.get(D_CONF, "")
            r_cnf = data.get(R_CONF, "")
            if d_cnf:
                d_cnf = float(d_cnf)
                if min_det_conf <= d_cnf <= max_det_conf:
                    self.settings.patch(key=D_CONF, value=d_cnf)
            if r_cnf:
                r_cnf = float(r_cnf)
                if min_rec_conf <= r_cnf <= max_rec_conf:
                    self.settings.patch(key=R_CONF, value=r_cnf)
            self.settings.patch(key=BASE_URL, value=get_base_url(
                url=data.get(LOGIN_URL, get_token_url)))
            self.settings.patch(key=BTN_DISABLE, value=data.get(BTN_DISABLE, True))
            self.settings.patch(key=SCALE_VIEW, value=data.get(SCALE_VIEW, False))
            self.settings.patch(key=SCALE_DISABLE, value=data.get(SCALE_DISABLE, False))
            self.config = self.settings.load()
            if data.get(USERNAME) and data.get(PASSWORD):
                self.login_thread.stop()
                self.login_thread.wait(1000)
                self.login_thread = LoginThread(
                    login_url=self.config.get(LOGIN_URL, get_token_url),
                    data={"login": self.config.get(USERNAME, default_username),
                          "password": self.config.get(PASSWORD, default_password)}
                )
                self.login_thread.login_signal.connect(self.login_response)
                self.login_thread.start()
                self.server_connection_thread.base_url = get_base_url(
                    url=self.config.get(LOGIN_URL, get_token_url))
            self.special_settings_dialog.close()
        except (Exception, ValueError) as err:
            show_message(stl=self.style_name, title="Xatolik",
                         message=f"[App.save_special_settings] {err}")
            log(message=f"[App.save_special_settings] {err}")
