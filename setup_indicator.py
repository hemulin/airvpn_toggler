import wx
import subprocess
import sys

"""
Adapted from http://stackoverflow.com/questions/6389580/quick-and-easy-trayicon-with-python#answer-6389727
"""

COUNTRY = ""

TRAY_TOOLTIP = 'Airvpn systray indicator'
TRAY_ICON = 'icon.jpg'

def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.AppendItem(item)
    return item

class TaskBarIcon(wx.TaskBarIcon):
    def __init__(self, frame):
        self.frame = frame
        super(TaskBarIcon, self).__init__()
        self.set_icon(TRAY_ICON)
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        create_menu_item(menu, 'Exiting from {}'.format(COUNTRY), None)
        menu.AppendSeparator()
        create_menu_item(menu, 'Turn Airvpn off', self.on_turn_off)
        return menu

    def set_icon(self, path):
        icon = wx.IconFromBitmap(wx.Bitmap(path))
        self.SetIcon(icon, TRAY_TOOLTIP)

    def on_left_down(self, event):
        # print 'Tray icon was left-clicked.'
        subprocess.Popen(['notify-send', "airvpn is running", "-t", "2000"])

    def on_turn_off(self, event):
        # print 'Turning off...'
        # wx.CallAfter(self.Destroy)
        # self.frame.Close()
        subprocess.Popen(["sudo", "python", "airvpn_toggler.py", "off"])

class App(wx.App):
    def OnInit(self):
        frame=wx.Frame(None)
        self.SetTopWindow(frame)
        TaskBarIcon(frame)
        return True

def setup():
    app = App(False)
    app.MainLoop()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        COUNTRY = "".join(sys.argv[1:])
    setup()