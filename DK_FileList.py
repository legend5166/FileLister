import os, re
import wx
import BaseUI
import csv
from datetime import datetime
import platform
if platform.architecture()[0] == '32bit':
	import formatter
else:
	import formatter_64 as formatter


class FileListFrame(BaseUI.FileListBaseUIFrame):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.root_folder = None
		self.folder_tree.Bind(wx.EVT_CONTEXT_MENU, self.OnTreeContextMenu)
		self.MakeTreeContextMenu()
		self.deleted_nodes = set()

	def OnBrowseBtn(self, evt):
		dlg = wx.DirDialog(self, '选择文件夹', '')
		if dlg.ShowModal() == wx.ID_OK:
			self.root_folder = os.path.abspath(dlg.GetPath())
			self.tc_folder_path.SetValue(self.root_folder)
			self._LoadFolderTree()
		dlg.Destroy()

	def _LoadFolderTree(self):
		"""目标文件夹内的所有子文件夹结构展示在 folder tree 中"""
		self.folder_tree.DeleteAllItems()
		if not self.root_folder:
			return

		root = self.folder_tree.AddRoot(os.path.basename(self.root_folder))
		self._AddTreeNodes(root, self.root_folder)
		self.folder_tree.Expand(root)
		self.deleted_nodes = set()

	def _AddTreeNodes(self, parent_item, folder_path):
		for item in os.listdir(folder_path):
			item_path = os.path.join(folder_path, item)
			if os.path.isdir(item_path):
				new_item = self.folder_tree.AppendItem(parent_item, item)
				self._AddTreeNodes(new_item, item_path)

	def OnTreeContextMenu(self, evt):
		if self.root_folder is None:
			return
		pos = evt.GetPosition()
		pos = self.folder_tree.ScreenToClient(pos)
		self.folder_tree.PopupMenu(self.tree_menu)

	def MakeTreeContextMenu(self):
		self.tree_menu = wx.Menu()
		delete = self.tree_menu.Append(wx.ID_ANY, '删除(&D)')
		restore = self.tree_menu.Append(wx.ID_ANY, '还原(&R)')
		self.Bind(wx.EVT_MENU, self.OnDeleteTreeNode, delete)
		self.Bind(wx.EVT_MENU, self.OnRestoreTree, restore)

	def OnDeleteTreeNode(self, evt):
		# 删除当前选中的节点
		item = self.folder_tree.GetSelection()
		if item.IsOk():
			root_item = self.folder_tree.GetRootItem()
			if root_item == item:
				wx.MessageBox('不可以删除根节点', '提示')
				return
			# 获取绝对路径
			path_parts = []
			current = item
			while current.IsOk() and current != root_item:
				path_parts.insert(0, self.folder_tree.GetItemText(current))
				current = self.folder_tree.GetItemParent(current)
			absolute_path = os.path.join(self.root_folder, *path_parts)
			self.deleted_nodes.add(absolute_path)
			self.folder_tree.Delete(item)

	def OnRestoreTree(self, evt):
		self._LoadFolderTree()

	def _GenerateHeader(self):
		header = ['文件名']
		if self.checkbox_size.GetValue():
			header.append('大小')
		if self.checkbox_create.GetValue():
			header.append('创建时间')
		if self.checkbox_modify.GetValue():
			header.append('修改时间')
		if self.checkbox_access.GetValue():
			header.append('访问时间')
		return header

	def GenerateFileList(self):
		"""生成文件清单"""
		root_file_before = self.rb_priority.GetSelection() == 0
		show_only_root = self.rb_priority.GetSelection() == 2
		file_format = self.rb_filename.GetSelection()
		include_types = self.rb_file_type.GetSelection() == 0
		type_filter = [t for t in re.split(r'[,; ]+', self.tc_file_type.GetValue().strip()) if t]
		show_size = self.checkbox_size.GetValue()
		show_create = self.checkbox_create.GetValue()
		show_modify = self.checkbox_modify.GetValue()
		show_access = self.checkbox_access.GetValue()

		file_list = []

		# 处理根目录文件
		if show_only_root:
			for file in os.listdir(self.root_folder):
				file_path = os.path.join(self.root_folder, file)
				if os.path.isfile(file_path):
					file_info = self._GetFileInfo(file_path, file_format, show_size, show_create, show_modify, show_access)
					if self._FilterFile(file_path, type_filter, include_types):
						yield file_info
			return

		# 递归处理文件夹
		for dirpath, dirnames, filenames in os.walk(self.root_folder, topdown=root_file_before):
			if not root_file_before:
				if any(dirpath.startswith(excluded) for excluded in self.deleted_nodes):
					continue
			else: #root_file_before is True
				dirnames[:] = [d for d in dirnames if os.path.join(dirpath, d) not in self.deleted_nodes]

			for file in filenames:
				file_path = os.path.join(dirpath, file)
				file_info = self._GetFileInfo(file_path, file_format, show_size, show_create, show_modify, show_access)
				if self._FilterFile(file_path, type_filter, include_types):
					yield file_info


	def _GetFileInfo(self, file_path, file_format, show_size, show_create, show_modify, show_access):
		"""根据用户选择获取文件信息"""
		if file_format == 1:
			display_name = os.path.relpath(file_path, self.root_folder)
		elif file_format == 2:
			display_name = file_path
		else:
			display_name = os.path.basename(file_path)

		file_info = [display_name]
		if show_size:
			file_info.append(formatter.format_file_size(os.path.getsize(file_path)))
		if show_create:
			file_info.append(datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%Y-%m-%d %H:%M:%S'))
		if show_modify:
			file_info.append(datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S'))
		if show_access:
			file_info.append(datetime.fromtimestamp(os.path.getatime(file_path)).strftime('%Y-%m-%d %H:%M:%S'))

		return file_info

	def _FilterFile(self, file_path, type_filter, include_types):
		"""根据文件类型过滤"""
		if not type_filter:
			return True

		file_ext = os.path.splitext(file_path)[1].lstrip('.')
		match = file_ext in type_filter
		return match if include_types else not match

	def OnFileTypeRb(self, evt):
		selection = evt.GetSelection()
		if selection == 0:
			self.lb_file_type.SetLabel('指定的文件类型[留空包含所有类型](&T)')
		elif selection == 1:
			self.lb_file_type.SetLabel('排除的文件类型[留空不排除任何类型](&T)')

	def OnPriorityRB(self, evt):
		selection = evt.GetSelection()
		if selection == 2: #仅根目录文件
			self.folder_tree.Disable()
		else:
			self.folder_tree.Enable()

	def OnGenerateFilelistBtn(self, event):
		if not self.root_folder:
			if (path:=self.tc_folder_path.GetValue()) and os.path.exists(path):
				self.root_folder = os.path.abspath(path)
				self._LoadFolderTree()
			else:
				wx.MessageBox('请先选择一个文件夹', '提示')
				return
		header = self._GenerateHeader()
		file_list = self.GenerateFileList()
		dlg = ShowFilelistDialog(self, -1, file_list=list(file_list), root_folder=self.root_folder)
		dlg.DisplayFileList(header)#, file_list)
		dlg.ShowModal()
		dlg.Destroy()

	def OnCloseBTN(self, evt):
		self.Close()



class FileListDialog(BaseUI.FileListBaseUIDialog):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.root_folder = None
		self.folder_tree.Bind(wx.EVT_CONTEXT_MENU, self.OnTreeContextMenu)
		self.MakeTreeContextMenu()
		self.deleted_nodes = set()

	def OnBrowseBtn(self, evt):
		dlg = wx.DirDialog(self, '选择文件夹', '')
		if dlg.ShowModal() == wx.ID_OK:
			self.root_folder = os.path.abspath(dlg.GetPath())
			self.tc_folder_path.SetValue(self.root_folder)
			self._LoadFolderTree()
		dlg.Destroy()

	def _LoadFolderTree(self):
		"""目标文件夹内的所有子文件夹结构展示在 folder tree 中"""
		self.folder_tree.DeleteAllItems()
		if not self.root_folder:
			return

		root = self.folder_tree.AddRoot(os.path.basename(self.root_folder))
		self._AddTreeNodes(root, self.root_folder)
		self.folder_tree.Expand(root)
		self.deleted_nodes = set()

	def _AddTreeNodes(self, parent_item, folder_path):
		for item in os.listdir(folder_path):
			item_path = os.path.join(folder_path, item)
			if os.path.isdir(item_path):
				new_item = self.folder_tree.AppendItem(parent_item, item)
				self._AddTreeNodes(new_item, item_path)

	def OnTreeContextMenu(self, evt):
		if self.root_folder is None:
			return
		pos = evt.GetPosition()
		pos = self.folder_tree.ScreenToClient(pos)
		self.folder_tree.PopupMenu(self.tree_menu)

	def MakeTreeContextMenu(self):
		self.tree_menu = wx.Menu()
		delete = self.tree_menu.Append(wx.ID_ANY, '删除(&D)')
		restore = self.tree_menu.Append(wx.ID_ANY, '还原(&R)')
		self.Bind(wx.EVT_MENU, self.OnDeleteTreeNode, delete)
		self.Bind(wx.EVT_MENU, self.OnRestoreTree, restore)

	def OnDeleteTreeNode(self, evt):
		# 删除当前选中的节点
		item = self.folder_tree.GetSelection()
		if item.IsOk():
			root_item = self.folder_tree.GetRootItem()
			if root_item == item:
				wx.MessageBox('不可以删除根节点', '提示')
				return
			# 获取绝对路径
			path_parts = []
			current = item
			while current.IsOk() and current != root_item:
				path_parts.insert(0, self.folder_tree.GetItemText(current))
				current = self.folder_tree.GetItemParent(current)
			absolute_path = os.path.join(self.root_folder, *path_parts)
			self.deleted_nodes.add(absolute_path)
			self.folder_tree.Delete(item)

	def OnRestoreTree(self, evt):
		self._LoadFolderTree()

	def _GenerateHeader(self):
		header = ['文件名']
		if self.checkbox_size.GetValue():
			header.append('大小')
		if self.checkbox_create.GetValue():
			header.append('创建时间')
		if self.checkbox_modify.GetValue():
			header.append('修改时间')
		if self.checkbox_access.GetValue():
			header.append('访问时间')
		return header

	def GenerateFileList(self):
		"""生成文件清单"""
		root_file_before = self.rb_priority.GetSelection() == 0
		show_only_root = self.rb_priority.GetSelection() == 2
		file_format = self.rb_filename.GetSelection()
		include_types = self.rb_file_type.GetSelection() == 0
		type_filter = [t for t in re.split(r'[,; ]+', self.tc_file_type.GetValue().strip()) if t]
		show_size = self.checkbox_size.GetValue()
		show_create = self.checkbox_create.GetValue()
		show_modify = self.checkbox_modify.GetValue()
		show_access = self.checkbox_access.GetValue()

		file_list = []

		# 处理根目录文件
		if show_only_root:
			for file in os.listdir(self.root_folder):
				file_path = os.path.join(self.root_folder, file)
				if os.path.isfile(file_path):
					file_info = self._GetFileInfo(file_path, file_format, show_size, show_create, show_modify, show_access)
					if self._FilterFile(file_path, type_filter, include_types):
						yield file_info
			return

		# 递归处理文件夹
		for dirpath, dirnames, filenames in os.walk(self.root_folder, topdown=root_file_before):
			if not root_file_before:
				if any(dirpath.startswith(excluded) for excluded in self.deleted_nodes):
					continue
			else: #root_file_before is True
				dirnames[:] = [d for d in dirnames if os.path.join(dirpath, d) not in self.deleted_nodes]

			for file in filenames:
				file_path = os.path.join(dirpath, file)
				file_info = self._GetFileInfo(file_path, file_format, show_size, show_create, show_modify, show_access)
				if self._FilterFile(file_path, type_filter, include_types):
					yield file_info


	def _GetFileInfo(self, file_path, file_format, show_size, show_create, show_modify, show_access):
		"""根据用户选择获取文件信息"""
		if file_format == 1:
			display_name = os.path.relpath(file_path, self.root_folder)
		elif file_format == 2:
			display_name = file_path
		else:
			display_name = os.path.basename(file_path)

		file_info = [display_name]
		if show_size:
			file_info.append(formatter.format_file_size(os.path.getsize(file_path)))
		if show_create:
			file_info.append(datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%Y-%m-%d %H:%M:%S'))
		if show_modify:
			file_info.append(datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S'))
		if show_access:
			file_info.append(datetime.fromtimestamp(os.path.getatime(file_path)).strftime('%Y-%m-%d %H:%M:%S'))

		return file_info

	def _FilterFile(self, file_path, type_filter, include_types):
		"""根据文件类型过滤"""
		if not type_filter:
			return True

		file_ext = os.path.splitext(file_path)[1].lstrip('.')
		match = file_ext in type_filter
		return match if include_types else not match

	def OnFileTypeRb(self, evt):
		selection = evt.GetSelection()
		if selection == 0:
			self.lb_file_type.SetLabel('指定的文件类型[留空包含所有类型](&T)')
		elif selection == 1:
			self.lb_file_type.SetLabel('排除的文件类型[留空不排除任何类型](&T)')

	def OnPriorityRB(self, evt):
		selection = evt.GetSelection()
		if selection == 2: #仅根目录文件
			self.folder_tree.Disable()
		else:
			self.folder_tree.Enable()

	def OnGenerateFilelistBtn(self, event):
		if not self.root_folder:
			if (path:=self.tc_folder_path.GetValue()) and os.path.exists(path):
				self.root_folder = os.path.abspath(path)
				self._LoadFolderTree()
			else:
				wx.MessageBox('请先选择一个文件夹', '提示')
				return
		header = self._GenerateHeader()
		file_list = self.GenerateFileList()
		dlg = ShowFilelistDialog(self, -1, file_list=list(file_list), root_folder=self.root_folder)
		dlg.DisplayFileList(header)#, file_list)
		dlg.ShowModal()
		dlg.Destroy()


class ShowFilelistDialog(BaseUI.ShowFileListDialog):
	def __init__(self, *args, file_list = [], root_folder='', **kwargs):
		super().__init__(*args, **kwargs)
		self.file_list = file_list
		self.SetTitle(f'文件清单 - 共{len(self.file_list)}个文件')
		self.root_folder = root_folder
		self.header = ['文件名']

	def DisplayFileList(self, header):#, file_list):
		"""在文本框中显示文件清单"""
		# self.file_list = list(file_list)
		self.header = header
		self.text_ctrl_1.SetValue('')

		rows = [','.join(row) for row in self.file_list]
		self.text_ctrl_1.SetValue('\n'.join([','.join(header)] + rows))

	def OnCopyBtn(self, event):
		if not self.file_list:
			return
		# data = '\n'.join([','.join(map(str, row)) for row in self.file_list])
		data = '\n'.join([','.join(row) for row in self.file_list])
		if wx.TheClipboard.Open() or wx.TheClipboard.IsOpened():
			wx.TheClipboard.SetData(wx.TextDataObject(data))
			wx.TheClipboard.Flush()
			wx.TheClipboard.Close()

	def OnSaveTxtBtn(self, event):
		self._SaveFile('txt')

	def OnSaveCsvBtn(self, event):
		self._SaveFile('csv')

	def _SaveFile(self, ext):
		if not self.file_list:
			return

		with wx.FileDialog(self, f"保存为{ext.upper()}文件", defaultFile=f'{os.path.basename(self.root_folder)}-文件清单', wildcard=f"*.{ext}", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
			if dlg.ShowModal() == wx.ID_OK:
				file_path = dlg.GetPath()
				with open(file_path, 'w', newline='', encoding='utf-8') as file:
					writer = csv.writer(file) if ext == 'csv' else file.write
					if ext == 'csv':
						writer.writerow(self.header)#['文件名', '大小', '创建时间', '修改时间'])
						writer.writerows(self.file_list)
					else:
						file.write('\n'.join([','.join(row) for row in self.file_list]))


class MyApp(wx.App):
	def OnInit(self):
		# self.dialog = FileListDialog(None, wx.ID_ANY, "")
		self.dialog = FileListFrame(None, wx.ID_ANY, "")
		self.SetTopWindow(self.dialog)
		self.dialog.Show()
		# if self.dialog.ShowModal() == wx.ID_CANCEL:
			# pass
		# self.dialog.Destroy()
		return True


if __name__ == "__main__":
	app = MyApp(0)
	app.MainLoop()
