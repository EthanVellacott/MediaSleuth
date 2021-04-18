#!/usr/bin/env python3

# external - default

import os
import math
import time
import webbrowser

# external - installed

import darkdetect
import wx
import wx.dataview

import pandas

# internal

import ext.systools as systools

from mediasleuth.platform import temp_directory
from mediasleuth.mediainspection_display import MediaInspectionDisplayItem
from mediasleuth.config import MediaSleuthConfig


'''
A note on shared dependencies
This is using the same ffmpeg module as you can see in the outsource tool
make sure to keep them up to date
'''
# CONSTANTS

DARK_LEVEL = 20
DATA_CELL_MIN_WIDTH = 120

# MAIN


def dark_mode_check():
    font_color = wx.BLACK
    bg_color = wx.WHITE
    # The following is patching a bug where dark mode only half works
    # However dark mode doesn't work at all before python3 wx, it appears
    # Getting dark mode actually working seems to be a little bit of a storied history
    # TODO work dark mode out once and for all
    if darkdetect.isDark():
        bg_color = wx.Colour(DARK_LEVEL, DARK_LEVEL, DARK_LEVEL)
        font_color = wx.WHITE
    return font_color, bg_color


class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, window):
        """Constructor"""
        wx.FileDropTarget.__init__(self)
        self.window = window

    def OnDropFiles(self, x, y, filenames):
        """
        When files are dropped, write where they were dropped and then
        the file paths themselves
        """
        print('Drop detected')

        for filepath in filenames:
            # self.window.updateText(filepath + '\n')
            # print(filepath)
            self.window.add_file_to_dataview(filepath)

        return True


def build_action_menuitem(appframe, parent_menu, wx_id, name, action_function):
    action = parent_menu.Append(wx_id, name)
    appframe.Bind(wx.EVT_MENU, action_function, action)


class MainWindow(wx.Frame):
    def __init__(self, app, *args):
        wx.Frame.__init__(self, *args)

        # Internal objects
        self.results = []
        self.config = MediaSleuthConfig().config

        # Set UI style - dark mode
        font_color, bg_color = dark_mode_check()
        self.SetBackgroundColour(bg_color)

        # Set up UI
        self.Bind(wx.EVT_CONTEXT_MENU, self.on_context)

        vbox = wx.BoxSizer(wx.VERTICAL)

        p = wx.Panel(self)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        # DATA TABLE
        self.dataview = wx.dataview.DataViewListCtrl(p, style=wx.EXPAND | wx.CENTRE | wx.dataview.DV_MULTIPLE)

        dt = MyFileDropTarget(self)
        self.SetDropTarget(dt)

        self.columns = []

        columns_layout = [
            # COLUMN NAME      FILL  WIDTH                      STYLE            HIDDEN
            ["FULL PATH",         1, DATA_CELL_MIN_WIDTH * 3,   wx.ALIGN_CENTRE, True],
            ["FROM FOLDER",       1, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, False],
            ["NAME",              1, DATA_CELL_MIN_WIDTH * 2,   wx.ALIGN_LEFT,   False],
            ["TIMECODE START",    0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, False],
            ["PICTURE START",     0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, False],
            ["FRAMES#",           0, 80,                        wx.ALIGN_CENTRE, False],
            ["FULL DURATION",     0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, False],
            ["PICTURE DURATION",  0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, False],
            ["HAS SLATE",         0, 100,                       wx.ALIGN_CENTRE, False],
            ["BLACK AT TAIL",     0, 100,                       wx.ALIGN_CENTRE, False],
            ["SLATE KEY",         0, DATA_CELL_MIN_WIDTH * 1.9, wx.ALIGN_CENTRE, False],
            ["OP48 AUDIO",        0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, False],
            ["OP59 AUDIO",        0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, False],
            ["AUDIO PEAK",        0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, True],
            ["RESOLUTION",        0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, True],
            ["FPS",               0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, True],
            ["BITRATE",           0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, True],
            ["VIDEO CODEC",       0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, True],
            ["AUDIO CODEC",       0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, True],
            ["AUDIO BITRATE",     0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, True],
            ["AUDIO SAMPLE RATE", 0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, True],
            ["SLATE DATE",        0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, True],
            ["SLATE ASPECT",      0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, True],
            ["SLATE DURATION",    0, DATA_CELL_MIN_WIDTH,       wx.ALIGN_CENTRE, True],

        ]

        for col in columns_layout:
            c = self.dataview.AppendTextColumn(col[0], col[1], width=math.floor(col[2]), align=col[3])
            c.SetSortable(True)
            c.SetHidden(col[4])
            self.columns.append(c)

        hbox.Add(self.dataview, 1, wx.EXPAND, 5)
        p.SetSizer(hbox)
        vbox.Add(p, 1, wx.EXPAND, 5)

        self.SetSizer(vbox)

        # MENU BAR

        menubar = wx.MenuBar()

        edit_menu = wx.Menu()
        menuitems = [
            [wx.ID_COPY,    "&Copy\tCtrl-C",               self.dataview_copy],
            [wx.ID_PRINT,   "&Print into browser\tCtrl-P", self.dataview_print],
            [wx.ID_REFRESH, "&Refresh Selected\tCtrl-R",   self.dataview_refresh_selected],
            [wx.ID_ANY,     "Select &All\tCtrl-A",         self.dataview_selectall],
            [wx.ID_CLEAR,   "Clear table",                 self.dataview_clear],
        ]
        for item in menuitems:
            build_action_menuitem(self, edit_menu, item[0], item[1], item[2])
        menubar.Append(edit_menu, "&Edit")

        view_menu = wx.Menu()
        menuitems = [
            [wx.ID_ANY, "Views", None],
        ]
        for item in menuitems:
            action = view_menu.Append(item[0], item[1])
            self.Bind(wx.EVT_MENU, item[2], action)
        menubar.Append(view_menu, "&View")

        help_menu = wx.Menu()
        menuitems = [
            [wx.ID_ANY,   "Getting started",             None],
            [wx.ID_ANY,   "Flush temp files",            self.tempfiles_flush],
            [wx.ID_ANY,   "About",                       None],
        ]
        for item in menuitems:
            build_action_menuitem(self, help_menu, item[0], item[1], item[2])
        menubar.Append(help_menu, "&Help")

        self.SetMenuBar(menubar)

        # SORT OUT WINDOW SIZING AND FIT
        # TODO rethink the window sizing

        self.SetMinSize((800, 400))
        self.Centre()

    def on_context(self, event):
        """
        At the moment there is only one context menu, and that is when you click on the table header

        This menu allows you to toggle what property columns are shown in the table view
        """
        print("Spawn context menu")

        """
        Uses a method from the following (but updated around deprecated API): 
         http://www.blog.pythonlibrary.org/2012/02/14/wxpython-all-about-menus/ (2019)
        """
        # build the menu
        menu = wx.Menu()
        for i, c in enumerate(self.columns):
            new_menu = menu.Append(wx.ID_ANY, c.GetTitle(), '', wx.ITEM_CHECK)
            self.Bind(wx.EVT_MENU, self.dataview_toggle_hidden_column, id=new_menu.Id)
            if not c.IsHidden():
                new_menu.Check()

        # show and end
        self.PopupMenu(menu)
        menu.Destroy()

        return 1

    def tempfiles_flush(self, event):
        """
        Delete all the temp working files
        Has a disclaimer that unfinished jobs will be in error

        TODO maybe this should also clear the dataview? dunno tho, the existing jobs may have been completed
        """
        dialog = wx.MessageDialog(self,
                                  "This will cause errors for any currently running checks.",
                                  "CAUTION",
                                  wx.ICON_WARNING | wx.OK | wx.CANCEL)

        # this cancels the operation if the user backs out
        if not dialog.ShowModal():
            return

        systools.rm(temp_directory())

    def dataview_clear(self):
        """
        Clear everything from the table
        NOTE : should not clear temp proxy files (shouldn't it?)

        To implement
        """
        pass

    def dataview_toggle_hidden_column(self, event):
        item_id = event.GetId()

        menu = event.GetEventObject()
        menuitem = menu.FindItemById(item_id)

        # this toggles, so do this either way
        menuitem.Check()

        column_name = menuitem.GetItemLabelText()

        print("Toggling column : ", column_name)
        column = self.dataview_get_column_by_name(column_name)
        column.SetHidden(not column.IsHidden())

    def dataview_get_column_by_name(self, name):
        matches = [x for x in self.columns if name == x.GetTitle()]
        if matches:
            return matches[-1]
        return

    def add_file_to_dataview(self, filepath):
        if self.get_row_by_file(filepath) is not None:
            print("Skipping existing file : {}".format(filepath))
            return

        print("Adding file to dataview : {}".format(filepath))

        new_item = MediaInspectionDisplayItem(self, filepath)

        self.results.append(new_item)

        item = self.dataview.AppendItem(new_item.display_results)
        new_item.item = item

        new_item.start_threads()

        # todo diagnose this problem - it may causes crashes
        # slow down the input of many files at once
        # not pleased about this fix, but it let's the work continue
        time.sleep(0.1)

    def replace_result_in_dataview(self, result):
        filepath = result.filepath

        print("Refreshing file in dataview : {}".format(filepath))

        new_item = MediaInspectionDisplayItem(self, filepath)

        target_index = self.results.index(result)
        self.results[target_index] = new_item

        new_item.item = result.item

        new_item.start_threads()

        # todo diagnose this problem - it may causes crashes
        # slow down the input of many files at once
        # not pleased about this fix, but it let's the work continue
        time.sleep(0.1)

    def get_row_by_file(self, filepath):
        c = self.dataview.GetItemCount()
        existing_files = [self.dataview.GetValue(x, 0) for x in range(0, c)]
        for i, f in enumerate(existing_files):
            if filepath == f:
                return i
        return None

    def get_result_by_filepath(self, filepath):
        for result in self.results:
            if filepath == result.filepath:
                return result
        return

    def dataview_refresh_selected(self, event=None):
        print("Refresh detected")
        selected_dataview_items = self.dataview.GetSelections()
        # selected_dataview_ids = [x.GetID() for x in selected_dataview_items]
        filepaths = []
        for item in selected_dataview_items:
            row = int(item.GetID()) - 1
            filepaths.append(self.dataview.GetValue(row, 0))

        for p in filepaths:
            old_result = self.get_result_by_filepath(p)
            self.replace_result_in_dataview(old_result)

    def dataview_print(self, event=None):
        print("Print detected")

        selected_dataview_items = self.dataview.GetSelections()

        header = []
        for i, c in enumerate(self.columns):
            if c.IsHidden():
                continue
            header.append(c.GetTitle())

        data_items = []

        for item in selected_dataview_items:
            row = int(item.GetID()) - 1
            rowdata = []
            for i, c in enumerate(self.columns):
                if c.IsHidden():
                    continue
                rowdata.append(self.dataview.GetValue(row, i))
            data_items.append(rowdata)

        # Attempt using pandas, flawed because it doesn't really work as hoped
        data = pandas.DataFrame(data_items, columns=header)
        html_data = data.to_html(header=True, index=False, justify='left', border=0)

        # TODO I can't figure out how to make the header not be bold - so, it's bold for now
        table_style = ('table-layout:fixed;'
                       'font-size:10pt;'
                       'font-family:arial,sans,sans-serif;'
                       'border-collapse:collapse;'
                       'padding:2px 10px 2px 10px;')
        th_style = ('text-align:center;'
                    'overflow:hidden;'
                    'padding:2px 10px 2px 10px;'
                    'vertical-align:bottom;'
                    'border-bottom: 1px solid black;')
        td_style = ('overflow:hidden;'
                    'padding:2px 10px 2px 10px;'
                    'vertical-align:bottom;'
                    'border-bottom: 1px solid black;')

        html_data = html_data.replace('class="dataframe"', 'class="table" style="{}"'.format(table_style))
        html_data = html_data.replace('<th>', '<th style="{}">'.format(th_style))
        html_data = html_data.replace('<td>', '<td style="{}">'.format(td_style))

        # todo put io elsewhere?
        systools.mkdir(temp_directory("table"))
        html_path = os.path.join(temp_directory("table"), 'mediasleuth_results.html')

        with open(html_path, 'w+') as f:
            f.write(html_data)

        webbrowser.open('file://{}'.format(html_path))

    def dataview_copy(self, event=None):
        print("Copy detected")
        # for each in selected, copy that text to the clipboard
        selected_dataview_items = self.dataview.GetSelections()

        header = []
        for i, c in enumerate(self.columns):
            if c.IsHidden():
                continue
            header.append(c.GetTitle())

        data_items = []
        for item in selected_dataview_items:
            row = int(item.GetID()) - 1
            rowdata = []
            for i, c in enumerate(self.columns):
                if c.IsHidden():
                    continue
                rowdata.append(self.dataview.GetValue(row, i))
            data_items.append(rowdata)

        # Attempt using pandas, flawed because it doesn't really work as hoped
        data = pandas.DataFrame(data_items, columns=header)

        # Todo work out using a lighter weight lib to do a similar thing
        # https://stackoverflow.com/questions/8356501/python-format-tabular-output/13537718 (2019)
        # data = tabulate(data_items)
        data = data.to_string(header=True, index=False, justify='left')

        text_data_object = wx.TextDataObject()
        text_data_object.SetText(data)

        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(text_data_object)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox("Can't open the clipboard", "Warning")

    def dataview_selectall(self, event=None):
        print("Select all detected")
        number_of_items = self.dataview.GetItemCount()
        if not number_of_items:
            return

        for i in range(0, number_of_items):
            self.dataview.SelectRow(i)


# Kick off the app runtime - Create a new app, don't redirect stdout/stderr to a window.
app = wx.App(False)
frame = MainWindow(app, None, wx.ID_ANY, "MediaSleuth")
app.SetTopWindow(frame)
frame.Show()

app.MainLoop()
