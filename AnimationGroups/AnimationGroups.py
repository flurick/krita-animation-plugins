from krita import *



# from PyKrita import *
# from PyQt5.QtWidgets import (QTreeView, QAbstractItemView, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox)
# from PyQt5.QtGui import QStandardItemModel, QStandardItem
# from PyQt5.QtCore import Qt, QModelIndex, pyqtSignal, QObject, QEvent
# from PyQt5.QtWidgets import QApplication
# from PyQt5.QtGui import QColor, QBrush
# Application = Krita.instance()
# DockWidgetFactory = Krita.instance().createDockWidgetFactory



class LayerItemModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def setData(self, index, value, role=Qt.EditRole):
        """Override to update layer name when item text is edited."""
        if role == Qt.EditRole and index.isValid():
            item = self.itemFromIndex(index)
            if item:
                node = item.data(Qt.UserRole)
                if node and hasattr(node, 'setName'):
                    try:
                        node.setName(value)
                        doc = Application.activeDocument()
                        if doc:
                            doc.refreshProjection()
                    except Exception as e:
                        print(f"Error renaming layer: {str(e)}")
                        return False
        return super().setData(index, value, role)




class AnimationGroups(DockWidget):
    def __init__(self):
        
        super().__init__()
        self.setWindowTitle("Groups")
        self.centralWidget = QWidget()
        layout = QVBoxLayout()
        self.centralWidget.setLayout(layout)

        # Create the tree view
        self.tree = QTreeView()
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Create model for the tree with columns for name, visibility, and pinned status
        self.tree_model = LayerItemModel()
        self.tree_model.setHorizontalHeaderLabels(['Name', 'Visible', 'Pinned', 'Children', 'Color'])
        
        # Configure the tree view
        #self.tree.setHeaderHidden(True)
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Reduce tree indentation for a more compact view
        self.tree.setIndentation(10)
        
        # Set the model for the tree view
        self.tree.setModel(self.tree_model)
        self.tree.selectionModel().selectionChanged.connect(self.update_tree)
        self.tree.setColumnHidden(1, True) #hide visible column
        self.tree.setColumnHidden(2, True) #hide pinned column

        # Add tree to layout with stretch to fill available space
        layout.addWidget(self.tree, 1)

        # Set slimmer column widths for all columns
        self.tree.setColumnWidth(0, 100)  # Group
        self.tree.setColumnWidth(1, 24)   # Visible
        self.tree.setColumnWidth(2, 24)   # Pinned
        self.tree.setColumnWidth(3, 24)   # Children
        self.tree.setColumnWidth(4, 24)   # Color

        # Sync the models with the document
        self.sync()
        self.setWidget(self.centralWidget)
        
        # Connect item changed signal once
        self.tree_model.itemChanged.connect(self.on_item_changed)
        
        # Connect mouse enter event
        self.setMouseTracking(True)
        self.enterEvent = self.on_mouse_enter
        # Add options
        self.optionLayout = QHBoxLayout()
        #self.optionLayout.addWidget(QLabel("Show:"))
        self.optionListLayers = QCheckBox("Layers")
        self.optionListLayers.setChecked(False)
        self.optionListLayers.stateChanged.connect(self.sync)
        self.optionLayout.addWidget(self.optionListLayers)
        layout.addLayout(self.optionLayout)
        self.optionListLayers.hide()


    def on_mouse_enter(self, event):
        self.sync() # Refresh the tree when the mouse enters dock, needs better syncing


    def add_children_to_tree(self, parent_item, node):
        """Recursively add group layer nodes to the tree with visibility and pinned status."""
        # First get all child nodes
        all_nodes = node.childNodes()
        if not all_nodes:
            return
            
        # Process in reverse order to maintain layer stack order

        color_map = {
            1: (91,173,220),      # Red
            2: (151,202,63),    # Orange
            3: (247,229,61),    # Yellow
            4: (255,170,63),      # Green
            5: (177,102,63),    # Blue
            6: (238,50,51),    # Purple
            7: (191,106,209),  # Gray
            8: (118,119,114),  # White
        }
        
        for child_node in reversed(all_nodes):
            # Always show color for all nodes
            # Optionally skip non-group layers if optionListLayers is not checked
            if not self.optionListLayers.isChecked() and child_node.type() != 'grouplayer':
                continue

            name_item = QStandardItem(child_node.name())
            visible_item = QStandardItem()
            pinned_item = QStandardItem()
            children_item = QStandardItem()
            color_item = QStandardItem()

            visible_icon = Application.icon('visible' if child_node.visible() else 'novisible')
            visible_item.setIcon(visible_icon)

            #pinned_item.setCheckable(True) #we dont really want the checkbox, just the toggle icon if even that much
            pinned_icon = Application.icon('krita_tool_reference_images' if child_node.isPinnedToTimeline() else '')
            pinned_item.setIcon(pinned_icon)

            child_count = len(child_node.childNodes())
            children_item.setText(str(child_count) if child_count > 0 else '')

            color_label = child_node.colorLabel()
            if color_label in color_map:
                rgb = color_map[color_label]
                color_item.setBackground(QColor(*rgb))
                color_item.setText('')
            else:
                color_item.setBackground(QBrush())
                color_item.setText('')

            name_item.setData(child_node, Qt.UserRole)
            row_items = [name_item, visible_item, pinned_item, children_item, color_item]
            if parent_item:
                parent_item.appendRow(row_items)
            else:
                self.tree_model.appendRow(row_items)

            # Recursively process child group layers
            self.add_children_to_tree(name_item, child_node)
        
    def on_item_changed(self, item):
        """Handle changes to item checkboxes for visibility and pinned status."""
        # Get the row of the changed item
        row = item.row()
        
        # Get all items in the row
        name_item = self.tree_model.item(row, 0)
        
        # Skip if this is not a valid row or we're missing items
        if not all([name_item]):
            return
            
        # Get the node from the name item
        node = name_item.data(Qt.UserRole)
        if not node:
            return
        
        # Update visibility
        if item.column() == 1:
            node.setVisible(item.checkState() == Qt.Checked)
        # Update pinned status
        if item.column() == 2:
            node.setPinnedToTimeline(item.checkState() == Qt.Checked)
        
    def update_tree(self, selected, deselected):
        """Handle selection changes in the tree view."""
        indexes = self.tree.selectedIndexes()
        item = self.tree_model.itemFromIndex(indexes[0])
        node = item.data(Qt.UserRole)
    
        if node.type() == 'grouplayer':
            self.pin_child_nodes(node)
        elif node.type() == 'paintlayer':
            self.select_layer(node)


    def select_layer(self, node):
        """Select the given layer in the document."""
        return 


    def pin_child_nodes(self, node):
        """Pin all non-group child nodes of the given node using Krita's pin action."""
        self.tree_model.blockSignals(True)
        try:
            doc = Application.activeDocument()
            if not doc:
                return
            
                
            pin_action = Krita.instance().action('pin_to_timeline')
            if not pin_action:
                return
                
            # Store current active node to restore it later
            last_active_layer = doc.activeNode()
            
            try:
                # First, unpin all currently pinned nodes
                for n in doc.rootNode().findChildNodes("", True, False, ""):
                    if hasattr(n, 'isPinnedToTimeline') and n.isPinnedToTimeline():
                        doc.setActiveNode(n)
                        pin_action.trigger()
                QApplication.processEvents() #wait for the unpin to finish (do we really need this?)

                # Pin the selected group if it's a Node
                if hasattr(node, 'type'):
                    doc.setActiveNode(node)
                    pin_action.trigger()

                    # Then pin all sub nodes 
                    last_layer_pinned = None
                    for child in node.findChildNodes("", True, False, ""):
                        if hasattr(child, 'visible') and child.visible(): #hidden layers are not pinned
                            doc.setActiveNode(child)
                            pin_action.trigger()
                            QApplication.processEvents() #may need this if krita crashes
                            last_layer_pinned = child

                    # Pin all parent groups up to but not including the root node
                    parent = node.parentNode()
                    while parent and parent.type() == 'grouplayer':# and parent != doc.rootNode():
                        doc.setActiveNode(parent)
                        pin_action.trigger()
                        QApplication.processEvents() #may need this if krita crashes
                        print(f"Pinning parent group: {parent.name()}")
                        parent = parent.parentNode()
            finally:
                if last_active_layer:
                    self.sync() #clears selected group hilight whne updating everything
                    
                    # Select layer again by name if it also exists in this group, otherwise select the bottom most visible layer
                    matching_name = node.findChildNodes(last_active_layer.name(), False, False, "")
                    if matching_name:
                        doc.setActiveNode(matching_name[0])
                    else:
                        doc.setActiveNode(last_layer_pinned)

                    self.tree_model.blockSignals(False)
                    
                    
        except Exception as e:
            print(f"Error in pin_child_nodes: {e}")


    def sync(self):
        """Synchronize the tree view with the current document's layer structure."""
        # Block signals during update to prevent unnecessary refreshes
        self.tree_model.blockSignals(True)
        
        try:
            # Clear the current model
            self.tree_model.clear()
            self.tree_model.setHorizontalHeaderLabels(['Name', 'Visible', 'Pinned', 'Children', 'Color'])
            
            doc = Application.activeDocument()
            if not doc:
                return
                
            root_node = doc.rootNode()
            if not root_node:
                return
            
            # List all group layers
            self.add_children_to_tree(None, root_node)
            
            # Expand all items by default
            self.tree.expandAll()
            
        except Exception as e:
            print(f"Error syncing layer tree: {e}")
        finally:
            # Always unblock signals when done
            self.tree_model.blockSignals(False)


    def canvasChanged(self, canvas):
        self.sync()

# Register the dock widget with Krita
Krita.instance().addDockWidgetFactory(DockWidgetFactory("AnimationGroups", DockWidgetFactoryBase.DockPosition.DockRight, AnimationGroups))