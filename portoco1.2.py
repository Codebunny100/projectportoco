import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QToolBar, QLineEdit,
    QTabBar, QMenu, QFileDialog, QInputDialog
)
from PySide6.QtGui import QAction, QFont, QKeySequence, QIcon
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtCore import QUrl, Qt, QSize

class Portoco(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Portoco")
        self.resize(1400, 900)

        # Data folder
        self.data_path = os.path.join(os.getcwd(), "portoco_data")
        os.makedirs(self.data_path, exist_ok=True)

        # Persistent profile
        self.profile = QWebEngineProfile.defaultProfile()
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

        # Bookmark button
        bookmark_btn = QAction("★", self)
        bookmark_btn.setStatusTip("Add current page to bookmarks")
        bookmark_btn.triggered.connect(self.add_bookmark)
        toolbar.addAction(bookmark_btn)

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
        self.history_menu = menubar.addMenu("History")

        # Data storage
        self.bookmarks = {}  # folder -> list of (url, title)
        self.history = {}    # tab -> list of urls

        # Shortcuts
        self.init_shortcuts()

        # Load persistent bookmarks/history
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
        view.setUrl(QUrl(url))
        view.setZoomFactor(1.0)
        self.history[view] = [url]

        # Signals
        view.urlChanged.connect(lambda u, v=view: self.update_url_bar(v))
        view.titleChanged.connect(lambda t, v=view: self.update_tab_title(v, t))
        view.urlChanged.connect(lambda u, v=view: self.update_history_menu(v))
        view.iconChanged.connect(lambda i, v=view: self.update_tab_icon(v, i))

        # Downloads
        self.setup_downloads(view)

        self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentWidget(view)
        view.setFocus()

    def close_tab(self, index):
        if self.tabs.count() > 1:
            tab = self.tabs.widget(index)
            if tab in self.history:
                del self.history[tab]
            self.tabs.removeTab(index)

    # Downloads
    def setup_downloads(self, view: QWebEngineView):
        page = view.page()
        page.profile().downloadRequested.connect(self.handle_download)

    def handle_download(self, download):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            download.downloadFileName()
        )
        if path:
            download.setPath(path)
            download.accept()

    # Navigation
    def load_url(self):
        text = self.url_bar.text().strip()
        if not text:
            return

        # Smart URL vs search
        tlds = [".com", ".net", ".org", ".io", ".gov", ".edu", ".co", ".us", ".uk", ".ca", ".de", ".jp"]
        if any(text.endswith(tld) for tld in tlds):
            if not text.startswith(("http://", "https://")):
                text = "http://" + text
        else:
            query = text.replace(" ", "+")
            text = f"https://duckduckgo.com/?q={query}"

        current = self.current_tab()
        if current:
            current.setUrl(QUrl(text))
            current.setFocus()
            if text not in self.history[current]:
                self.history[current].append(text)
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

        folder, ok = QInputDialog.getText(self, "Bookmark Folder", "Folder name:", text="Bookmarks")
        if not ok or not folder.strip():
            folder = "Bookmarks"
        folder = folder.strip()

        if folder not in self.bookmarks:
            self.bookmarks[folder] = []

        if url in [b[0] for b in self.bookmarks[folder]]:
            return

        self.bookmarks[folder].append((url, title))
        self.build_bookmarks_menu()

    def remove_bookmark(self, folder, url):
        if folder in self.bookmarks:
            self.bookmarks[folder] = [b for b in self.bookmarks[folder] if b[0] != url]
            if not self.bookmarks[folder]:
                del self.bookmarks[folder]
            self.build_bookmarks_menu()

    def build_bookmarks_menu(self):
        self.bookmarks_menu.clear()
        for folder, bookmarks in self.bookmarks.items():
            folder_menu = QMenu(folder, self)
            folder_menu.setTearOffEnabled(True)
            for url, title in bookmarks:
                action = QAction(title, self)
                action.triggered.connect(lambda checked, u=url: self.load_bookmark(u))
                folder_menu.addAction(action)

                remove_action = QAction(f"Remove '{title}'", self)
                remove_action.triggered.connect(lambda checked, f=folder, u=url: self.remove_bookmark(f, u))
                folder_menu.addAction(remove_action)

            self.bookmarks_menu.addMenu(folder_menu)

    def load_bookmark(self, url):
        current = self.current_tab()
        current.setUrl(QUrl(url))
        current.setFocus()

    def save_bookmarks(self):
        path = os.path.join(self.data_path, "bookmarks.txt")
        with open(path, "w", encoding="utf-8") as f:
            for folder, bookmarks in self.bookmarks.items():
                for url, title in bookmarks:
                    f.write(f"{folder}|{title}|{url}\n")

    def load_bookmarks(self):
        path = os.path.join(self.data_path, "bookmarks.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("|", 2)
                    if len(parts) != 3:
                        continue
                    folder, title, url = parts
                    if folder not in self.bookmarks:
                        self.bookmarks[folder] = []
                    self.bookmarks[folder].append((url, title))
        self.build_bookmarks_menu()

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
    Copyright (c) 2026 Poniek Labs Canada
    Licensed under the Portoco License - see LICENSE file for details'''
