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
    QToolBar,
    QPushButton,
)
from PySide6.QtGui import QAction, QKeySequence, QIcon, QPalette
from PySide6.QtCore import QUrl, Qt, QSize
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage


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
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        
        # Performance optimizations
        settings = self.profile.settings()
        settings.setAttribute(settings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(settings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(settings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(settings.WebAttribute.AllowRunningInsecureContent, False)
        
        # Enable HTTP/2
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        self.profile.setHttpCacheMaximumSize(100 * 1024 * 1024)  # 100MB cache

        # ---------- bookmarks ----------
        self.bookmarks = {}  # folder -> [(title, url)]

        # ---------- detect dark mode ----------
        self.is_dark_mode = self.is_system_dark_mode()

        # ---------- UI ----------
        self.init_ui()
        self.init_menu()
        self.init_shortcuts()
        self.apply_styles()

        # ---------- first tab ----------
        self.add_tab("https://duckduckgo.com")

    def is_system_dark_mode(self):
        """Detect if system is in dark mode"""
        palette = QApplication.palette()
        bg_color = palette.color(QPalette.ColorRole.Window)
        # If background is dark (luminance < 128), it's dark mode
        return bg_color.lightness() < 128

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Navigation toolbar
        nav_toolbar = QToolBar()
        nav_toolbar.setMovable(False)
        nav_toolbar.setIconSize(QSize(14, 14))
        nav_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(nav_toolbar)

        # Back button
        back_btn = QAction("←", self)
        back_btn.setToolTip("Back")
        back_btn.triggered.connect(self.navigate_back)
        nav_toolbar.addAction(back_btn)

        # Forward button
        forward_btn = QAction("→", self)
        forward_btn.setToolTip("Forward")
        forward_btn.triggered.connect(self.navigate_forward)
        nav_toolbar.addAction(forward_btn)

        # Reload button
        reload_btn = QAction("⟳", self)
        reload_btn.setToolTip("Reload")
        reload_btn.triggered.connect(self.reload_page)
        nav_toolbar.addAction(reload_btn)

        nav_toolbar.addSeparator()

        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search or enter URL...")
        self.url_bar.returnPressed.connect(self.navigate)
        nav_toolbar.addWidget(self.url_bar)

        # New tab button
        new_tab_btn = QPushButton("+")
        new_tab_btn.setToolTip("New Tab (Ctrl+T)")
        new_tab_btn.setFixedSize(24, 24)
        new_tab_btn.clicked.connect(lambda: self.add_tab("https://duckduckgo.com"))
        nav_toolbar.addWidget(new_tab_btn)

        # Bookmark button
        bookmark_btn = QAction("⭐", self)
        bookmark_btn.setToolTip("Add Bookmark")
        bookmark_btn.triggered.connect(self.add_bookmark)
        nav_toolbar.addAction(bookmark_btn)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.sync_url_bar)

        layout.addWidget(self.tabs)

    def apply_styles(self):
        if self.is_dark_mode:
            # Dark mode styles
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1e1e1e;
                }
                
                QToolBar {
                    background-color: #2d2d2d;
                    border-bottom: 1px solid #3d3d3d;
                    padding: 3px;
                    spacing: 3px;
                }
                
                QToolBar QToolButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 3px;
                    padding: 3px 6px;
                    font-size: 13px;
                    color: #ffffff;
                }
                
                QToolBar QToolButton:hover {
                    background-color: #3d3d3d;
                }
                
                QToolBar QToolButton:pressed {
                    background-color: #4d4d4d;
                }
                
                QLineEdit {
                    border: 1px solid #3d3d3d;
                    border-radius: 12px;
                    padding: 4px 10px;
                    background-color: #1e1e1e;
                    font-size: 12px;
                    color: #ffffff;
                }
                
                QLineEdit:focus {
                    border: 1px solid #4a90e2;
                    background-color: #2d2d2d;
                }
                
                QPushButton {
                    background-color: #3d3d3d;
                    border: 1px solid #4d4d4d;
                    border-radius: 12px;
                    font-size: 14px;
                    font-weight: bold;
                    color: #ffffff;
                }
                
                QPushButton:hover {
                    background-color: #4d4d4d;
                    border-color: #5d5d5d;
                }
                
                QPushButton:pressed {
                    background-color: #5d5d5d;
                }
                
                QTabWidget::pane {
                    border: none;
                    background-color: #2d2d2d;
                }
                
                QTabBar::tab {
                    background-color: #2d2d2d;
                    border: none;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    padding: 5px 10px;
                    margin-right: 2px;
                    min-width: 80px;
                    max-width: 180px;
                    color: #b0b0b0;
                    font-size: 12px;
                }
                
                QTabBar::tab:selected {
                    background-color: #1e1e1e;
                    border-bottom: 2px solid #4a90e2;
                    color: #ffffff;
                }
                
                QTabBar::tab:hover:!selected {
                    background-color: #3d3d3d;
                    color: #ffffff;
                }
                
                QTabBar::close-button {
                    image: none;
                    subcontrol-position: right;
                    background-color: #d32f2f;
                    border-radius: 2px;
                    padding: 2px;
                    width: 12px;
                    height: 12px;
                }
                
                QTabBar::close-button:hover {
                    background-color: #f44336;
                }
                
                QMenu {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 3px;
                    color: #ffffff;
                }
                
                QMenu::item {
                    padding: 4px 20px;
                    border-radius: 3px;
                }
                
                QMenu::item:selected {
                    background-color: #4a90e2;
                    color: #ffffff;
                }
            """)
        else:
            # Light mode styles
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f5f5;
                }
                
                QToolBar {
                    background-color: #ffffff;
                    border-bottom: 1px solid #e0e0e0;
                    padding: 3px;
                    spacing: 3px;
                }
                
                QToolBar QToolButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 3px;
                    padding: 3px 6px;
                    font-size: 13px;
                    color: #000000;
                }
                
                QToolBar QToolButton:hover {
                    background-color: #e8e8e8;
                }
                
                QToolBar QToolButton:pressed {
                    background-color: #d0d0d0;
                }
                
                QLineEdit {
                    border: 1px solid #d0d0d0;
                    border-radius: 12px;
                    padding: 4px 10px;
                    background-color: #f8f8f8;
                    font-size: 12px;
                    color: #000000;
                }
                
                QLineEdit:focus {
                    border: 1px solid #4a90e2;
                    background-color: #ffffff;
                }
                
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #d0d0d0;
                    border-radius: 12px;
                    font-size: 14px;
                    font-weight: bold;
                    color: #555;
                }
                
                QPushButton:hover {
                    background-color: #e0e0e0;
                    border-color: #b0b0b0;
                }
                
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
                
                QTabWidget::pane {
                    border: none;
                    background-color: #ffffff;
                }
                
                QTabBar::tab {
                    background-color: #e8e8e8;
                    border: none;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    padding: 5px 10px;
                    margin-right: 2px;
                    min-width: 80px;
                    max-width: 180px;
                    color: #555555;
                    font-size: 12px;
                }
                
                QTabBar::tab:selected {
                    background-color: #ffffff;
                    border-bottom: 2px solid #4a90e2;
                    color: #000000;
                }
                
                QTabBar::tab:hover:!selected {
                    background-color: #d8d8d8;
                }
                
                QTabBar::close-button {
                    image: none;
                    subcontrol-position: right;
                    background-color: #d32f2f;
                    border-radius: 2px;
                    padding: 2px;
                    width: 12px;
                    height: 12px;
                }
                
                QTabBar::close-button:hover {
                    background-color: #f44336;
                }
                
                QMenu {
                    background-color: #ffffff;
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    padding: 3px;
                    color: #000000;
                }
                
                QMenu::item {
                    padding: 4px 20px;
                    border-radius: 3px;
                }
                
                QMenu::item:selected {
                    background-color: #4a90e2;
                    color: #ffffff;
                }
            """)

    # --------------------------------------------------
    # Navigation Controls
    # --------------------------------------------------

    def navigate_back(self):
        current = self.current_tab()
        if current:
            current.back()

    def navigate_forward(self):
        current = self.current_tab()
        if current:
            current.forward()

    def reload_page(self):
        current = self.current_tab()
        if current:
            current.reload()

    # --------------------------------------------------
    # Tabs
    # --------------------------------------------------

    def add_tab(self, url=None):
        # Create a page with the profile first
        page = QWebEnginePage(self.profile, self)
        
        # Create view and set the page
        view = QWebEngineView()
        view.setPage(page)

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
            # Limit tab title length
            if len(title) > 20:
                title = title[:17] + "..."
            self.tabs.setTabText(i, title)
        if view == self.tabs.currentWidget():
            self.url_bar.setText(qurl.toString())

    def current_tab(self):
        return self.tabs.currentWidget()

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

        self.current_tab().setUrl(QUrl(text))

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

    def init_shortcuts(self):
        new_tab = QAction(self)
        new_tab.setShortcut(QKeySequence("Ctrl+T"))
        new_tab.triggered.connect(
            lambda: self.add_tab("https://duckduckgo.com")
        )
        self.addAction(new_tab)

    # --------------------------------------------------
    # Bookmarks
    # --------------------------------------------------

    def add_bookmark(self):
        current = self.current_tab()
        if not current:
            return

        url = current.url().toString()
        title = current.page().title() or url

        folders = list(self.bookmarks.keys())

        # Folder selector
        if folders:
            folder, ok = QInputDialog.getItem(
                self,
                "Choose Bookmark Folder",
                "Select a folder:",
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
            folder, ok = QInputDialog.getText(
                self,
                "New Folder",
                "Folder name:",
                text="Bookmarks"
            )
            if not ok or not folder.strip():
                return
            folder = folder.strip()

        if folder not in self.bookmarks:
            self.bookmarks[folder] = []

        # Prevent duplicates
        if url in [u for _, u in self.bookmarks[folder]]:
            return

        self.bookmarks[folder].append((title, url))
        self.build_bookmarks_menu()

    def build_bookmarks_menu(self):
        self.bookmarks_menu.clear()

        add_bm = QAction("Add Bookmark", self)
        add_bm.triggered.connect(self.add_bookmark)
        self.bookmarks_menu.addAction(add_bm)
        self.bookmarks_menu.addSeparator()

        for folder, bookmarks in self.bookmarks.items():
            folder_menu = QMenu(folder, self)
            for title, url in bookmarks:
                action = QAction(title, self)
                action.triggered.connect(
                    lambda checked=False, u=url: self.current_tab().setUrl(QUrl(u))
                )
                folder_menu.addAction(action)
            self.bookmarks_menu.addMenu(folder_menu)


# --------------------------------------------------
# Run
# --------------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    browser = Portoco()
    browser.show()
    sys.exit(app.exec())
