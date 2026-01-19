import sys
import os

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QTabWidget,
    QMenu,
    QInputDialog,
)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile


# --------------------------------------------------
# Main Window
# --------------------------------------------------

class Portoco(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Portoco")
        self.resize(1200, 800)

        # ---------- data folder ----------
        self.data_path = os.path.join(os.getcwd(), "portoco_data")
        os.makedirs(self.data_path, exist_ok=True)

        # ---------- web profile ----------
        self.profile = QWebEngineProfile("PortocoProfile", self)
        self.profile.setPersistentStoragePath(self.data_path)
        self.profile.setCachePath(self.data_path)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.ForcePersistentCookies
        )

        # ---------- bookmarks ----------
        self.bookmarks = {}  # folder -> [(title, url)]

        # ---------- UI ----------
        self.init_ui()
        self.init_menu()
        self.init_shortcuts()

        # ---------- first tab ----------
        self.add_tab("https://duckduckgo.com")

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.sync_url_bar)

        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate)

        layout.addWidget(self.tabs)
        layout.addWidget(self.url_bar)

    # --------------------------------------------------
    # Tabs
    # --------------------------------------------------

    def add_tab(self, url=None):
        view = QWebEngineView()
        view.page().setProfile(self.profile)

        if url:
            view.setUrl(QUrl(url))

        index = self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentIndex(index)

        view.urlChanged.connect(
            lambda qurl, v=view: self.update_tab(v, qurl)
        )
        view.loadFinished.connect(
            lambda _, v=view: self.update_tab(v, v.url())
        )

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)

    def update_tab(self, view, qurl):
        i = self.tabs.indexOf(view)
        if i != -1:
            title = view.page().title() or "New Tab"
            self.tabs.setTabText(i, title)
        if view == self.tabs.currentWidget():
            self.url_bar.setText(qurl.toString())

    # --------------------------------------------------
    # Navigation
    # --------------------------------------------------

    def navigate(self):
        text = self.url_bar.text().strip()
        if not text:
            return

        if " " in text or "." not in text:
            text = f"https://duckduckgo.com/?q={text.replace(' ', '+')}"
        elif not text.startswith("http"):
            text = "https://" + text

        self.tabs.currentWidget().setUrl(QUrl(text))

    def sync_url_bar(self, index):
        view = self.tabs.widget(index)
        if view:
            self.url_bar.setText(view.url().toString())

    # --------------------------------------------------
    # Menu
    # --------------------------------------------------

    def init_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        new_tab = QAction("New Tab", self)
        new_tab.triggered.connect(
            lambda: self.add_tab("https://duckduckgo.com")
        )
        file_menu.addAction(new_tab)

        self.bookmarks_menu = menubar.addMenu("Bookmarks")
        add_bm = QAction("Add Bookmark", self)
        add_bm.triggered.connect(self.add_bookmark)
        self.bookmarks_menu.addAction(add_bm)
        self.bookmarks_menu.addSeparator()

    # --------------------------------------------------
    # Bookmarks
    # --------------------------------------------------

def add_bookmark(self):
    current = self.current_tab()
    if not current:
        return

    url = current.url().toString()
    title = current.title() or url

    folders = list(self.bookmarks.keys())

    # If folders exist, let user choose
    if folders:
        folder, ok = QInputDialog.getItem(
            self,
            "Choose Bookmark Folder",
            "Select a folder or create a new one:",
            folders + ["➕ Create new folder"],
            0,
            False
        )
        if not ok:
            return

        if folder == "➕ Create new folder":
            folder, ok = QInputDialog.getText(
                self,
                "New Folder",
                "Folder name:"
            )
            if not ok or not folder.strip():
                return
            folder = folder.strip()
    else:
        # No folders exist yet
        folder, ok = QInputDialog.getText(
            self,
            "New Folder",
            "Folder name:",
            text="Bookmarks"
        )
        if not ok or not folder.strip():
            return
        folder = folder.strip()

    # Create folder if missing
    if folder not in self.bookmarks:
        self.bookmarks[folder] = []

    # Prevent duplicates
    if url in [b[0] for b in self.bookmarks[folder]]:
        return

    self.bookmarks[folder].append((url, title))
    self.build_bookmarks_menu()
