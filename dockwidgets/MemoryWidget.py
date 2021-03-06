from PySide2 import QtCore
from PySide2.QtCore import Qt, QAbstractItemModel, QModelIndex, QSize
from PySide2.QtGui import QPalette, QFontMetricsF
from PySide2.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout, QWidget, QTableView, QItemDelegate, QStyle, QHeaderView, QAbstractItemView

import binaryninja
import binaryninjaui
from binaryninja import BinaryView
from binaryninjaui import DockContextHandler, UIActionHandler, LinearView, ViewFrame

from . import widget
from .. import binjaplug

class DebugMemoryWidget(QWidget, DockContextHandler):
	def __init__(self, parent, name, data):
		if not type(data) == binaryninja.binaryview.BinaryView:
			raise Exception('expected widget data to be a BinaryView')

		self.bv = data

		memory_view = binjaplug.get_state(data).memory_view

		QWidget.__init__(self, parent)
		DockContextHandler.__init__(self, self, name)

		self.editor = LinearView(memory_view, ViewFrame.viewFrameForWidget(self))
		self.actionHandler = UIActionHandler()
		self.actionHandler.setupActionHandler(self)

		layout = QVBoxLayout()
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(0)
		layout.addWidget(self.editor)
		self.setLayout(layout)

	def notifyOffsetChanged(self, offset):
		pass

	def notifyMemoryChanged(self):
		debug_state = binjaplug.get_state(self.bv)

		# Refresh the editor
		if not debug_state.connected:
			self.editor.navigate(0)
			return

		self.editor.navigate(debug_state.stack_pointer)

	def shouldBeVisible(self, view_frame):
		if view_frame is None:
			return False
		else:
			return True

