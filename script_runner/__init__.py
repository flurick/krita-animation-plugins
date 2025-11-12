#--- START OF FILE __init__.py ---

import krita
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QMessageBox, QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem
)
from PyQt5.QtCore import Qt, QUrl, QSize, QRect, QPointF
from PyQt5.QtGui import QDesktopServices, QFont, QColor, QPainter, QPolygonF

from pathlib import Path
import traceback
import sys
import os
# --- MODIFICATION: New imports for cross-platform support ---
import platform
import subprocess

# --- Plugin Configuration ---
PLUGIN_ID = "krita_script_runner"
PLUGIN_NAME = "Script Runner"
DOCKER_TITLE = "Script Runner"
SCRIPTS_SUBFOLDER = "scripts"
MAX_SCRIPT_SEARCH_DEPTH = 3 

# --- UI Configuration (User changeable) ---
BUTTON_HEIGHT = 22                      # Overall height of the buttons
BUTTON_HORIZONTAL_PADDING = 6           # Padding on the left/right inside each button
BUTTON_GROUP_SPACING = 2                # Gap between buttons in the main group
TREE_ITEM_INDENTATION = 10
TREE_ITEM_HEIGHT = 16
FOLDER_BG_COLOR = QColor(191, 191, 191)
FOLDER_TEXT_COLOR = Qt.black
ARROW_COLOR = Qt.darkGray
ARROW_SIZE = 7
ARROW_PADDING = 4
TEXT_PADDING_AFTER_ARROW = 4


# --- MODIFICATION: Cross-platform helper to open files ---
def open_with_default_app(filepath):
    """Opens a file with the system's default application."""
    filepath = str(filepath) # Ensure it's a string
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(filepath)
        elif system == "Darwin": # macOS
            subprocess.run(["open", filepath], check=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", filepath], check=True)
        else:
            raise RuntimeError(f"Unsupported OS for opening files: {system}")
    except FileNotFoundError:
        # This can happen on Linux if xdg-open is not installed
        QMessageBox.critical(None, "Error", f"Could not find the command to open the file. Is the required tool (e.g., xdg-open) installed?")
    except Exception as e:
        QMessageBox.critical(None, "Error Opening File", f"An error occurred while trying to open the file:\n{e}")

# --- Custom Delegate for Tree Items ---
class FolderItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        item_type = index.data(Qt.UserRole + 1)
        is_folder = (item_type == "folder")
        
        is_selected = False
        is_expanded = False
        if hasattr(option, 'state'):
            is_selected = bool(option.state & QStyle.State_Selected)
            is_expanded = bool(option.state & QStyle.State_Open)
            
        painter.save()

        bg_color = option.palette.base().color()
        if is_folder:
            bg_color = FOLDER_BG_COLOR
        if is_selected:
            bg_color = option.palette.highlight().color()
        
        painter.fillRect(option.rect, bg_color)

        content_rect = QRect(option.rect)
        text_x_offset = content_rect.left() + ARROW_PADDING

        if is_folder:
            actual_arrow_size = min(ARROW_SIZE, content_rect.height() - 2 * ARROW_PADDING)
            if actual_arrow_size < 4: actual_arrow_size = 4

            arrow_y = content_rect.top() + (content_rect.height() - actual_arrow_size) // 2
            arrow_x = content_rect.left() + ARROW_PADDING
            
            poly = QPolygonF()
            arrow_center_y = arrow_y + actual_arrow_size / 2

            if is_expanded: 
                poly.append(QPointF(arrow_x, arrow_center_y - actual_arrow_size / 3))
                poly.append(QPointF(arrow_x + actual_arrow_size, arrow_center_y - actual_arrow_size / 3))
                poly.append(QPointF(arrow_x + actual_arrow_size / 2, arrow_center_y + actual_arrow_size * 2 / 3))
            else:
                poly.append(QPointF(arrow_x + actual_arrow_size / 3, arrow_center_y - actual_arrow_size / 2))
                poly.append(QPointF(arrow_x + actual_arrow_size / 3, arrow_center_y + actual_arrow_size / 2))
                poly.append(QPointF(arrow_x + actual_arrow_size * 2 / 3, arrow_center_y))
            
            brush_color = ARROW_COLOR
            if is_selected:
                brush_color = option.palette.highlightedText().color() 
            painter.setBrush(brush_color)
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(poly)

            text_x_offset = arrow_x + actual_arrow_size + TEXT_PADDING_AFTER_ARROW
        
        text_rect = QRect(text_x_offset, content_rect.top(),
                          content_rect.width() - (text_x_offset - content_rect.left()) - ARROW_PADDING,
                          content_rect.height())
        
        text = index.data(Qt.DisplayRole)
        
        item_font = QFont(option.font)
        text_color = option.palette.text().color()

        if is_folder:
            item_font.setBold(True)
        
        if is_selected:
            text_color = option.palette.highlightedText().color()
        elif is_folder :
             text_color = FOLDER_TEXT_COLOR

        painter.setFont(item_font)
        painter.setPen(text_color)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        size = super().sizeHint(option, index)
        size.setHeight(TREE_ITEM_HEIGHT)
        return size

class ScriptRunnerDocker(krita.DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(DOCKER_TITLE)

        self.scripts_dir = Path(__file__).parent / SCRIPTS_SUBFOLDER
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

        main_widget = QWidget(self)
        self.setWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        top_bar_layout = QHBoxLayout()
        top_bar_layout.setSpacing(0)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        button_style = f"""
            QPushButton {{
                height: {BUTTON_HEIGHT}px;
                padding-left: {BUTTON_HORIZONTAL_PADDING}px;
                padding-right: {BUTTON_HORIZONTAL_PADDING}px;
                margin-right: {BUTTON_GROUP_SPACING}px;
            }}
        """

        self.execute_button = QPushButton("Execute")
        self.execute_button.setStyleSheet(button_style)
        self.execute_button.clicked.connect(self.execute_selected_script)
        self.execute_button.setToolTip("Run the selected script")
        top_bar_layout.addWidget(self.execute_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setStyleSheet(button_style)
        self.refresh_button.clicked.connect(self.refresh_script_list)
        self.refresh_button.setToolTip("Reload the list of scripts and folders")
        top_bar_layout.addWidget(self.refresh_button)

        self.edit_button = QPushButton("Edit")
        self.edit_button.setStyleSheet(button_style)
        self.edit_button.clicked.connect(self.edit_selected_script)
        self.edit_button.setToolTip("Edit the selected script in your default text editor")
        top_bar_layout.addWidget(self.edit_button)

        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.setStyleSheet(button_style)
        self.open_folder_button.clicked.connect(self.open_selected_item_folder)
        self.open_folder_button.setToolTip("Open the folder of the selected item")
        top_bar_layout.addWidget(self.open_folder_button)

        top_bar_layout.addStretch(1)

        self.go_home_button = QPushButton()
        inst = krita.Krita.instance()
        icon = inst.icon("go-home")
        self.go_home_button.setIcon(icon)
        self.go_home_button.clicked.connect(self.open_scripts_folder)
        self.go_home_button.setToolTip(f"Open the root '{SCRIPTS_SUBFOLDER}' folder")
        self.go_home_button.setFixedSize(BUTTON_HEIGHT, BUTTON_HEIGHT)
        top_bar_layout.addWidget(self.go_home_button)
        layout.addLayout(top_bar_layout)

        self.script_tree_widget = QTreeWidget()
        self.script_tree_widget.setHeaderHidden(True)
        self.script_tree_widget.setAlternatingRowColors(False)
        self.script_tree_widget.setIndentation(TREE_ITEM_INDENTATION)
        self.script_tree_widget.setRootIsDecorated(False)

        self.script_tree_widget.setStyleSheet("""
            QTreeWidget::branch:closed:has-children,
            QTreeWidget::branch:open:has-children {
                image: none;
                border-image: none;
            }
            QTreeWidget::branch {
                background: transparent;
            }
        """)

        delegate = FolderItemDelegate(self.script_tree_widget)
        self.script_tree_widget.setItemDelegate(delegate)

        self.script_tree_widget.itemDoubleClicked.connect(self.handle_item_double_clicked)
        self.script_tree_widget.currentItemChanged.connect(self._update_button_states)
        self.script_tree_widget.itemClicked.connect(self.on_tree_item_clicked)

        layout.addWidget(self.script_tree_widget)

        main_widget.setMinimumSize(200, 100)
        self.setMinimumSize(200, 150)

        self.refresh_script_list()
        self._update_button_states()

    def on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        if item and item.data(0, Qt.UserRole + 1) == "folder":
            item.setExpanded(not item.isExpanded())
            self.script_tree_widget.viewport().update()

    def _update_button_states(self):
        current_item = self.script_tree_widget.currentItem()
        is_script_selected = (
            current_item is not None and
            current_item.data(0, Qt.UserRole + 1) == "script"
        )
        is_folder_selected = (
            current_item is not None and
            current_item.data(0, Qt.UserRole + 1) == "folder"
        )
        self.execute_button.setEnabled(is_script_selected)
        self.edit_button.setEnabled(is_script_selected)
        self.open_folder_button.setEnabled(is_script_selected or is_folder_selected)

    def handle_item_double_clicked(self, item, column):
        if item and item.data(0, Qt.UserRole + 1) == "script":
            self.execute_selected_script()
        elif item and item.data(0, Qt.UserRole + 1) == "folder":
            item.setExpanded(not item.isExpanded())
            self.script_tree_widget.viewport().update()

    def refresh_script_list(self):
        current_selection_path = None
        current_item = self.script_tree_widget.currentItem()
        if current_item and current_item.data(0, Qt.UserRole):
            current_selection_path = current_item.data(0, Qt.UserRole)
        
        expanded_folders_paths = set()
        def collect_expanded_folders(parent_item, expanded_set):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                item_type = child.data(0, Qt.UserRole + 1)
                if item_type == "folder":
                    folder_path = child.data(0, Qt.UserRole)
                    if folder_path and child.isExpanded():
                        expanded_set.add(folder_path)
                    collect_expanded_folders(child, expanded_set) 

        collect_expanded_folders(self.script_tree_widget.invisibleRootItem(), expanded_folders_paths)

        self.script_tree_widget.clear()
        
        if not self.scripts_dir.exists():
            try:
                self.scripts_dir.mkdir(parents=True, exist_ok=True)
                QMessageBox.information(self, "Scripts Folder Created",
                                    f"The scripts folder '{self.scripts_dir}' was created. Add Python scripts (.py) and subfolders.")
            except Exception as e:
                QMessageBox.critical(self, "Error Creating Scripts Folder", f"Could not create '{self.scripts_dir}':\n{e}")
                placeholder_item = QTreeWidgetItem(self.script_tree_widget, ["Error: Scripts folder issue"])
                placeholder_item.setFlags(placeholder_item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
                placeholder_item.setData(0, Qt.UserRole + 1, "placeholder")
                self._update_button_states()
                return

        found_any_content = False
        new_current_item_to_select = None

        def populate_tree(parent_widget_item, current_dir_path: Path, current_depth: int):
            nonlocal new_current_item_to_select, found_any_content
            try:
                items_in_dir = sorted(
                    list(current_dir_path.iterdir()),
                    key=lambda p: (not p.is_dir(), p.name.lower())
                )
            except OSError as e: 
                print(f"ScriptRunner: Could not access directory {current_dir_path}: {e}")
                return
            for item_path in items_in_dir:
                if item_path.is_file() and item_path.suffix.lower() == ".py":
                    tree_item = QTreeWidgetItem(parent_widget_item, [item_path.stem])
                    tree_item.setData(0, Qt.UserRole, item_path)
                    tree_item.setData(0, Qt.UserRole + 1, "script")
                    found_any_content = True
                    if item_path == current_selection_path:
                        new_current_item_to_select = tree_item
                elif item_path.is_dir() and item_path.name != "__pycache__":
                    folder_item = QTreeWidgetItem(parent_widget_item, [item_path.name])
                    folder_item.setData(0, Qt.UserRole, item_path)
                    folder_item.setData(0, Qt.UserRole + 1, "folder")
                    found_any_content = True
                    if item_path == current_selection_path:
                        new_current_item_to_select = folder_item
                    if item_path in expanded_folders_paths:
                        folder_item.setExpanded(True)
                    else:
                        folder_item.setExpanded(False) 
                    if current_depth < MAX_SCRIPT_SEARCH_DEPTH:
                        populate_tree(folder_item, item_path, current_depth + 1)

        populate_tree(self.script_tree_widget, self.scripts_dir, 0)
        if not found_any_content:
            placeholder_item = QTreeWidgetItem(self.script_tree_widget, [f"No items in '{SCRIPTS_SUBFOLDER}'"])
            placeholder_item.setFlags(placeholder_item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
            placeholder_item.setData(0, Qt.UserRole + 1, "placeholder")
        if new_current_item_to_select:
            self.script_tree_widget.setCurrentItem(new_current_item_to_select)
        elif self.script_tree_widget.topLevelItemCount() > 0:
            first_item = self.script_tree_widget.topLevelItem(0)
            if first_item and (first_item.flags() & Qt.ItemIsSelectable):
                 self.script_tree_widget.setCurrentItem(first_item)
        self._update_button_states()
        self.script_tree_widget.viewport().update()

    def edit_selected_script(self):
        current_item = self.script_tree_widget.currentItem()
        if not current_item or current_item.data(0, Qt.UserRole + 1) != "script":
            return
        
        script_file_path = current_item.data(0, Qt.UserRole)
        if isinstance(script_file_path, Path) and script_file_path.is_file():
            # --- MODIFICATION: Use the cross-platform helper function ---
            open_with_default_app(script_file_path.resolve())
        else:
            QMessageBox.critical(self, "Error", f"Script path error or file not found: {script_file_path}. Please refresh the list.")
            self.refresh_script_list()

    def execute_selected_script(self):
        current_item = self.script_tree_widget.currentItem()
        if not current_item or current_item.data(0, Qt.UserRole + 1) != "script":
            QMessageBox.information(self, "No Script Selected", "Please select a valid script item to execute.")
            return
        script_file_path = current_item.data(0, Qt.UserRole)
        if not isinstance(script_file_path, Path) or not script_file_path.exists():
            QMessageBox.critical(self, "Error", f"Script path error: {script_file_path}. Refresh list.")
            self.refresh_script_list()
            return
        try:
            modules_to_remove = []
            scripts_parent_dir_abs_str = str(script_file_path.parent.resolve())
            main_scripts_dir_abs_str = str(self.scripts_dir.resolve())
            for module_name, mod in list(sys.modules.items()):
                if hasattr(mod, '__file__') and mod.__file__:
                    try:
                        module_file_path_resolved = Path(mod.__file__).resolve()
                        module_dir_abs_str = str(module_file_path_resolved.parent)
                        if module_dir_abs_str == main_scripts_dir_abs_str or \
                           module_dir_abs_str == scripts_parent_dir_abs_str or \
                           (module_name.startswith(SCRIPTS_SUBFOLDER + ".") and \
                            (main_scripts_dir_abs_str in str(module_file_path_resolved) or \
                             scripts_parent_dir_abs_str in str(module_file_path_resolved))):
                            if module_name not in ("__main__", "__main_script_runner__") and \
                               module_name not in sys.builtin_module_names:
                                modules_to_remove.append(module_name)
                    except Exception: pass
            for module_name in modules_to_remove:
                if module_name in sys.modules:
                    print(f"--- ScriptRunner: Unloading module '{module_name}' for fresh execution. ---")
                    del sys.modules[module_name]
            with open(script_file_path, 'r', encoding='utf-8') as f: script_code = f.read()
            script_scope = {
                "__file__": str(script_file_path.resolve()),
                "__name__": "__main_script_runner__", 
                "krita_app": krita.Krita.instance(),
            }
            print(f"--- EXECUTING SCRIPT: {script_file_path.name} (in {script_file_path.parent.name if script_file_path.parent != self.scripts_dir else SCRIPTS_SUBFOLDER}) ---")
            exec(script_code, script_scope, script_scope) 
            print(f"--- FINISHED SCRIPT: {script_file_path.name} ---")
        except Exception as e:
            error_message = f"--- SCRIPT EXECUTION ERROR: {script_file_path.name} ---\n\n{type(e).__name__}: {e}\n\nTraceback:\n{traceback.format_exc()}\n--- END ERROR ---"
            print(error_message)
            QMessageBox.critical(self, "Script Execution Error", error_message)

    def open_selected_item_folder(self):
        current_item = self.script_tree_widget.currentItem()
        if not current_item:
            return
        item_path = current_item.data(0, Qt.UserRole)
        if isinstance(item_path, Path):
            folder_to_open = item_path.parent if item_path.is_file() else item_path
            if not folder_to_open.exists():
                QMessageBox.warning(self, "Folder Not Found", f"Could not find folder:\n{folder_to_open}")
                return
            # This is already cross-platform thanks to Qt
            url = QUrl.fromLocalFile(str(folder_to_open.resolve()))
            if not QDesktopServices.openUrl(url):
                QMessageBox.warning(self, "Could Not Open Folder", f"Could not open:\n{folder_to_open}")

    def open_scripts_folder(self):
        if not self.scripts_dir.exists():
            QMessageBox.information(self, "Folder Not Found", f"'{self.scripts_dir}' missing. Attempting creation.")
            try: self.scripts_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                 QMessageBox.warning(self, "Could Not Create Folder", f"Failed to create {self.scripts_dir}:\n{e}")
                 return
        # This is already cross-platform thanks to Qt
        url = QUrl.fromLocalFile(str(self.scripts_dir.resolve()))
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(self, "Could Not Open Folder", f"Could not open:\n{self.scripts_dir}")

    def canvasChanged(self, canvas):
        pass

class ScriptRunnerDockerFactory(krita.DockWidgetFactory):
    def __init__(self): super().__init__(PLUGIN_ID, krita.DockWidgetFactoryBase.DockRight, ScriptRunnerDocker)
    def createDocker(self): return ScriptRunnerDocker()

try:
    krita_instance = krita.Krita.instance()
    if krita_instance is None: print(f"Error: No Krita instance for {PLUGIN_NAME}.")
    else:
        factory = ScriptRunnerDockerFactory()
        krita_instance.addDockWidgetFactory(factory)
        print(f"--- Plugin {PLUGIN_NAME} loaded. ---")
except AttributeError: print(f"Error: Krita API changed? {PLUGIN_NAME} not registered.")
except Exception as e:
    print(f"Unexpected error registering {PLUGIN_NAME}: {e}")
    traceback.print_exc()