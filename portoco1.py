import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QToolBar, QLineEdit,
    QTabBar, QMenu, QFileDialog
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtCore import QUrl, Qt, QSize
from PySide6.QtGui import QAction, QFont, QKeySequence, QIcon  # <-- QAction MUST come from QtGui


class Portoco(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Portoco")
        self.resize(1400, 900)

        # Data folder
        self.data_path = os.path.join(os.getcwd(), "portoco_data")
        os.makedirs(self.data_path, exist_ok=True)

        # Persistent profile
        self.profile = QWebEngineProfile("Portoco", self)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        self.profile.setPersistentStoragePath(self.data_path)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_url)
        self.tabs.setDocumentMode(True)
        self.tabs.setElideMode(Qt.ElideRight)
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                height: 36px;
                width: 220px;
                font-size: 13pt;
                padding: 5px;
            }
        """)
        self.setCentralWidget(self.tabs)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(32, 32))
        toolbar.setStyleSheet("QToolBar { spacing: 10px; padding: 5px; }")
        self.addToolBar(toolbar)

        # Navigation buttons
        back_btn = QAction("←", self)
        back_btn.triggered.connect(lambda: self.current_tab().back())
        toolbar.addAction(back_btn)

        forward_btn = QAction("→", self)
        forward_btn.triggered.connect(lambda: self.current_tab().forward())
        toolbar.addAction(forward_btn)

        reload_btn = QAction("⟳", self)
        reload_btn.triggered.connect(lambda: self.current_tab().reload())
        toolbar.addAction(reload_btn)

        # Address bar
        self.url_bar = QLineEdit()
        self.url_bar.setMinimumHeight(32)
        self.url_bar.setFont(QFont("Segoe UI", 12))
        self.url_bar.returnPressed.connect(self.load_url)
        toolbar.addWidget(self.url_bar)

        # New tab button
        new_tab_btn = QAction("+", self)
        new_tab_btn.triggered.connect(lambda: self.add_tab("https://duckduckgo.com"))
        toolbar.addAction(new_tab_btn)

        # Menu: Bookmarks & History
        menubar = self.menuBar()
        self.bookmarks_menu = menubar.addMenu("Bookmarks")
        self.add_bookmark_action = QAction("Add Current Page", self)
        self.add_bookmark_action.triggered.connect(self.add_bookmark)
        self.bookmarks_menu.addAction(self.add_bookmark_action)
        self.bookmarks_list = []

        self.history_menu = menubar.addMenu("History")
        self.history = {}  # tab -> list of urls

        # Shortcuts
        self.init_shortcuts()

        # Load persistent bookmarks and history
        self.load_bookmarks()
        self.load_history()

        # Open first tab
        self.add_tab("https://duckduckgo.com")

        # Save on exit
        app.aboutToQuit.connect(self.save_bookmarks)
        app.aboutToQuit.connect(self.save_history)

    # Shortcuts
    def init_shortcuts(self):
        new_tab_sc = QAction(self)
        new_tab_sc.setShortcut(QKeySequence("Ctrl+T"))
        new_tab_sc.triggered.connect(lambda: self.add_tab("https://duckduckgo.com"))
        self.addAction(new_tab_sc)

        close_tab_sc = QAction(self)
        close_tab_sc.setShortcut(QKeySequence("Ctrl+W"))
        close_tab_sc.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        self.addAction(close_tab_sc)

        focus_bar_sc = QAction(self)
        focus_bar_sc.setShortcut(QKeySequence("Ctrl+L"))
        focus_bar_sc.triggered.connect(lambda: self.url_bar.setFocus())
        self.addAction(focus_bar_sc)

        # Ctrl+Tab / Ctrl+Shift+Tab
        next_tab_sc = QAction(self)
        next_tab_sc.setShortcut(QKeySequence("Ctrl+Tab"))
        next_tab_sc.triggered.connect(lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex()+1)%self.tabs.count()))
        self.addAction(next_tab_sc)

        prev_tab_sc = QAction(self)
        prev_tab_sc.setShortcut(QKeySequence("Ctrl+Shift+Tab"))
        prev_tab_sc.triggered.connect(lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex()-1)%self.tabs.count()))
        self.addAction(prev_tab_sc)

    def current_tab(self):
        return self.tabs.currentWidget()

    # Tabs
    def add_tab(self, url):
        view = QWebEngineView()
        view.setPage(QWebEnginePage(self.profile, view))
        view.setUrl(QUrl(url))
        view.setZoomFactor(1.0)
        self.history[view] = [url]

        # Update address bar and tab title
        view.urlChanged.connect(lambda u, v=view: self.update_url_bar(v))
        view.titleChanged.connect(lambda t, v=view: self.update_tab_title(v, t))
        view.urlChanged.connect(lambda u, v=view: self.update_history_menu(v))
        view.iconChanged.connect(lambda i, v=view: self.update_tab_icon(v, i))

        # Downloads
        view.page().profile().downloadRequested.connect(self.handle_download)

        self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentWidget(view)
        view.setFocus()

    def close_tab(self, index):
        if self.tabs.count() > 1:
            tab = self.tabs.widget(index)
            if tab in self.history:
                del self.history[tab]
            self.tabs.removeTab(index)

    # Navigation
    def load_url(self):
        url_text = self.url_bar.text().strip()
        if not url_text:
            return
        if not url_text.startswith(("http://","https://")):
            url_text = "http://" + url_text
        current = self.current_tab()
        if current:
            current.setUrl(QUrl(url_text))
            current.setFocus()
            if url_text not in self.history[current]:
                self.history[current].append(url_text)
            self.update_history_menu(current.url())

    def update_url_bar(self, view):
        url = view.url().toString()
        if view == self.current_tab():
            self.url_bar.setText(url)
        if url not in self.history[view]:
            self.history[view].append(url)
        self.update_history_menu(view.url())

    def update_tab_title(self, view, title):
        index = self.tabs.indexOf(view)
        if index >= 0:
            self.tabs.setTabText(index, title)

    def update_tab_icon(self, view, icon: QIcon):
        index = self.tabs.indexOf(view)
        if index >= 0:
            self.tabs.setTabIcon(index, icon)

    # Bookmarks
    def add_bookmark(self):
        current = self.current_tab()
        url = current.url().toString()
        title = current.title() or url
        if url not in [b[0] for b in self.bookmarks_list]:
            self.bookmarks_list.append((url, title))
            action = QAction(title, self)
            action.triggered.connect(lambda checked, u=url: self.load_bookmark(u))
            self.bookmarks_menu.addAction(action)
            self.save_bookmarks()

    def load_bookmark(self, url):
        current = self.current_tab()
        current.setUrl(QUrl(url))
        current.setFocus()

    def save_bookmarks(self):
        path = os.path.join(self.data_path, "bookmarks.txt")
        with open(path, "w", encoding="utf-8") as f:
            for url, title in self.bookmarks_list:
                f.write(f"{title}|{url}\n")

    def load_bookmarks(self):
        path = os.path.join(self.data_path, "bookmarks.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    title, url = line.strip().split("|", 1)
                    self.bookmarks_list.append((url, title))
                    action = QAction(title, self)
                    action.triggered.connect(lambda checked, u=url: self.load_bookmark(u))
                    self.bookmarks_menu.addAction(action)

    # History
    def update_history_menu(self, qurl):
        self.history_menu.clear()
        current = self.current_tab()
        if current:
            for url in reversed(self.history[current]):
                action = QAction(url, self)
                action.triggered.connect(lambda checked, u=url: self.load_history(u))
                self.history_menu.addAction(action)

    def load_history(self, url):
        current = self.current_tab()
        current.setUrl(QUrl(url))
        current.setFocus()

    def save_history(self):
        path = os.path.join(self.data_path, "history.txt")
        with open(path, "w", encoding="utf-8") as f:
            for tab, urls in self.history.items():
                for url in urls:
                    f.write(f"{url}\n")

    def load_history(self):
        path = os.path.join(self.data_path, "history.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    if self.current_tab():
                        self.history[self.current_tab()].append(url)

    # Downloads
    def handle_download(self, download):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", download.path())
        if path:
            download.setPath(path)
            download.accept()

    # Update address bar when switching tabs
    def update_url(self, index):
        view = self.tabs.widget(index)
        if view:
            self.url_bar.setText(view.url().toString())
            view.setFocus()

# Main
if __name__ == "__main__":
    app = QApplication(sys.argv)
    browser = Portoco()
    browser.show()
    sys.exit(app.exec())


''' Made by Erik W for Poniek Labs Canada
    Copyright 2026 Poniek Labs Canada Licensed
    under the GNU General Public License v3.0
    https://labs.poniek.ca'''
