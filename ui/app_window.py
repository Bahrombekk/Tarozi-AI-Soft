from __future__ import annotations

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtWidgets import QMessageBox

from core.config import log
from threads.workers import ScaleThread
from utils.helpers import open_all_scales as _open_all_scales
from utils.helpers import ask_message


class WindowMixin:

    @staticmethod
    def _time_format(tm: int) -> str:
        return f"{tm // 3600:02}:{(tm % 3600) // 60:02}:{tm % 60:02}"

    def find_scales(self):
        try:
            self.scales = _open_all_scales()
            self.com_ports = [str(s.port) for s in self.scales]
        except (Exception, ValueError) as err:
            log(message=f"[App.find_scales] {err}")

    def closeEvent(self, a0):
        try:
            ans = ask_message(stl=self.style_name, title="Chiqish",
                              message="Dasturdan chiqishni tasdiqlaysizmi?")
            if ans == QMessageBox.StandardButton.Yes:
                def _stop(t):
                    if t is None:
                        return
                    try:
                        t.running = False
                        if not t.wait(2000):
                            t.terminate()
                    except Exception:
                        pass
                _stop(self.video_thread_left)
                _stop(self.video_thread_right)
                _stop(self.server_connection_thread)
                _stop(self.login_thread)
                if isinstance(self.scale_thread, ScaleThread):
                    self.scale_thread.stop()
                try:
                    self.backup_db.close()
                except Exception:
                    pass
                a0.accept()
            else:
                a0.ignore()
        except (Exception, ValueError) as err:
            log(message=f"[App.closeEvent] {err}")
            a0.accept()

    def eventFilter(self, obj, ev):
        et = ev.type()
        if obj is self.title_widget:
            if et == QEvent.Type.MouseButtonDblClick and ev.button() == Qt.MouseButton.LeftButton:
                self.show_toggle()
                return True
            if et == QEvent.Type.MouseButtonPress and ev.button() == Qt.MouseButton.LeftButton:
                if self.windowHandle():
                    self.windowHandle().startSystemMove()
                    return True
        if et == QEvent.Type.MouseMove:
            if not self.isMaximized() and not getattr(self, "_is_maximized", False):
                pos = self.mapFromGlobal(ev.globalPosition().toPoint())
                self._update_cursor_shape(pos)
            else:
                self.unsetCursor()
            return False
        if et == QEvent.Type.MouseButtonPress and ev.button() == Qt.MouseButton.LeftButton:
            if not self.isMaximized() and not getattr(self, "_is_maximized", False):
                pos = self.mapFromGlobal(ev.globalPosition().toPoint())
                dirs = self._hit_test(pos)
                if dirs and self.windowHandle():
                    edges = self._qt_edges_from_direction(dirs)
                    if edges:
                        self._resizing = True
                        self.windowHandle().startSystemResize(edges)
                        return True
        if et == QEvent.Type.MouseButtonRelease:
            if self._resizing:
                self._resizing = False
                self.unsetCursor()
            try:
                pos = self.mapFromGlobal(ev.globalPosition().toPoint())
                self._update_cursor_shape(pos)
            except (Exception, ValueError):
                self.unsetCursor()
            return False
        return super(type(self), self).eventFilter(obj, ev)

    @staticmethod
    def _qt_edges_from_direction(d: str) -> Qt.Edge:
        edges = Qt.Edge(0)
        if 'left' in d:
            edges |= Qt.Edge.LeftEdge
        if 'right' in d:
            edges |= Qt.Edge.RightEdge
        if 'top' in d:
            edges |= Qt.Edge.TopEdge
        if 'bottom' in d:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _hit_test(self, pos):
        x, y, w, h, bw = pos.x(), pos.y(), self.width(), self.height(), 5
        left, right, top, bottom = x <= bw, x >= w - bw, y <= bw, y >= h - bw
        if top and left:
            return 'topleft'
        if top and right:
            return 'topright'
        if bottom and left:
            return 'bottomleft'
        if bottom and right:
            return 'bottomright'
        if left:
            return 'left'
        if right:
            return 'right'
        if top:
            return 'top'
        if bottom:
            return 'bottom'
        return None

    def _update_cursor_shape(self, pos):
        d = self._hit_test(pos)
        cursors = {
            'left': Qt.CursorShape.SizeHorCursor, 'right': Qt.CursorShape.SizeHorCursor,
            'top': Qt.CursorShape.SizeVerCursor, 'bottom': Qt.CursorShape.SizeVerCursor,
            'topleft': Qt.CursorShape.SizeFDiagCursor, 'bottomright': Qt.CursorShape.SizeFDiagCursor,
            'topright': Qt.CursorShape.SizeBDiagCursor, 'bottomleft': Qt.CursorShape.SizeBDiagCursor,
        }
        self.setCursor(cursors.get(d, Qt.CursorShape.ArrowCursor))

    def show_toggle(self):
        if self.isMinimized():
            self.showNormal()
            return
        if getattr(self, "_is_maximized", False):
            self._is_maximized = False
            self.showNormal()
            if hasattr(self, "_normal_geometry"):
                self.setGeometry(self._normal_geometry)
        else:
            self._normal_geometry = self.geometry()
            self._is_maximized = True
            from PyQt6.QtWidgets import QApplication
            avail = QApplication.primaryScreen().availableGeometry()
            self.setGeometry(avail)
