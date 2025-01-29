import os
import wx
import BaseUI
import csv
from datetime import datetime

class FileListDialog(BaseUI.FileListBaseUIDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_folder = None
        self.folder_tree.Bind(wx.EVT_CONTEXT_MENU, self.OnTreeContextMenu)
        self.MakeTreeContextMenu()
        self.deleted_nodes = []

    def OnBrowseBtn(self, evt):
        dlg = wx.DirDialog(self, '选择文件夹', '')
        if dlg.ShowModal() == wx.ID_OK:
            self.root_folder = dlg.GetPath()
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
        item = self.folder_tree.GetSelection()
        if item.IsOk():
            self.deleted_nodes.append(self.folder_tree.GetItemText(item))
            self.folder_tree.Delete(item)

    def OnRestoreTree(self, evt):
        self._LoadFolderTree()

    def GenerateFileList(self):
        """生成文件清单"""
        if not self.root_folder:
            return []

        show_only_root = self.rb_priority.GetSelection() == 2
        file_format = self.rb_filename.GetSelection()
        include_types = self.rb_file_type.GetSelection() == 0
        type_filter = self.tc_file_type.GetValue().strip().split(',')
        show_size = self.checkbox_size.GetValue()
        show_create = self.checkbox_create.GetValue()
        show_modify = self.checkbox_modify.GetValue()

        file_list = []

        for dirpath, dirnames, filenames in os.walk(self.root_folder):
            if show_only_root and dirpath != self.root_folder:
                continue

            if dirnames:
                dirnames[:] = [d for d in dirnames if d not in self.deleted_nodes]

            for file in filenames:
                file_ext = os.path.splitext(file)[1].lstrip('.')
                if type_filter:
                    match = file_ext in type_filter
                    if (include_types and not match) or (not include_types and match):
                        continue

                file_path = os.path.join(dirpath, file)
                if file_format == 1:
                    display_name = os.path.relpath(file_path, self.root_folder)
                elif file_format == 2:
                    display_name = file_path
                else:
                    display_name = file

                file_info = [display_name]

                if show_size:
                    file_info.append(os.path.getsize(file_path))
                if show_create:
                    file_info.append(datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%Y-%m-%d %H:%M:%S'))
                if show_modify:
                    file_info.append(datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S'))

                file_list.append(file_info)

        return file_list

class ShowFilelistDialog(BaseUI.ShowFileListDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_list = []

    def DisplayFileList(self, file_list):
        """在文本框中显示文件清单"""
        self.file_list = file_list
        self.text_ctrl_1.SetValue('')
        if not file_list:
            self.text_ctrl_1.SetValue('没有可显示的文件清单')
            return

        header = ['文件名']
        if len(file_list[0]) > 1:
            header += ['大小', '创建时间', '修改时间'][:len(file_list[0]) - 1]

        rows = [','.join(map(str, row)) for row in file_list]
        self.text_ctrl_1.SetValue('\n'.join([','.join(header)] + rows))

    def OnCopyBtn(self, event):
        if not self.file_list:
            return
        data = '\n'.join([','.join(map(str, row)) for row in self.file_list])
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(data))
            wx.TheClipboard.Close()

    def OnSaveTxtBtn(self, event):
        self._SaveFile('txt')

    def OnSaveCsvBtn(self, event):
        self._SaveFile('csv')

    def _SaveFile(self, ext):
        if not self.file_list:
            return

        with wx.FileDialog(self, f"保存为{ext.upper()}文件", wildcard=f"*.{ext}", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                file_path = dlg.GetPath()
                with open(file_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file) if ext == 'csv' else file.write
                    if ext == 'csv':
                        writer.writerow(['文件名', '大小', '创建时间', '修改时间'])
                        writer.writerows(self.file_list)
                    else:
                        file.write('\n'.join([','.join(map(str, row)) for row in self.file_list]))

class MyApp(wx.App):
    def OnInit(self):
        self.dialog = FileListDialog(None, wx.ID_ANY, "")
        self.SetTopWindow(self.dialog)
        if self.dialog.ShowModal() == wx.ID_OK:
            file_list = self.dialog.GenerateFileList()
            dlg = ShowFilelistDialog(self.dialog, -1)
            dlg.DisplayFileList(file_list)
            dlg.ShowModal()
            dlg.Destroy()
        self.dialog.Destroy()
        return True

if __name__ == "__main__":
    app = MyApp(0)
    app.MainLoop()
