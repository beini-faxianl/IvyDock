import sys, os, json, webbrowser, markdown
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QToolButton,
    QPushButton, QSplitter, QLineEdit, QDialog, QFormLayout, QComboBox,
    QFileDialog, QMessageBox, QTreeWidget, QTreeWidgetItem, QMenu,
    QTextEdit, QLabel, QSpinBox, QDialogButtonBox, QTabWidget, QPlainTextEdit
)
from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QIcon
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
from matplotlib import rcParams

# 可选 Windows 深色模式检测
try:
    import winreg
except ImportError:
    winreg = None

# 全局常量
SETTINGS_FILE = "settings.json"
TOOLS_FILE    = "tools_data.json"
USAGE_LOG     = "usage_log.json"

DEFAULT_SETTINGS = {
    "theme":"System",
    "font_size":10,
    "window_width":1800,
    "window_height":1200,
    "language":"中文",
    "python_path":"python"      # 新增：默认解释器命令
}


I18N = {
    "中文":{
        "app_title":"工具管理平台","search":"搜索工具...",
        "add_tool":"+ 添加工具","select_detail":"选择一个工具查看详情",
        "settings":"应用设置","about":"关于信息",
        "theme":"主题","light":"浅色","dark":"暗黑","system":"随系统",
        "font_size":"字体大小","window_size":"初始窗口大小","language":"系统语言",
        "ok":"确定","cancel":"取消",
        "name":"名称","type":"类型","url":"网址","category":"分类",
        "path":"执行文件","args":"默认参数","simple_description":"说明",
        "browse":"浏览文件…","import_doc":"导入说明文档…",
        "add":"添加","edit":"编辑","delete":"删除",
        "confirm_delete":"确认删除","launch_error":"启动失败",
        "restart_prompt":"设置已保存，需要重启后生效，立即重启？",
        "recent_usage":"近期工具使用情况",
        "opt_py_cli": "命令行Python工具",
        "opt_py_exec": "可执行Python工具",
        "today_top5":"今日使用 Top5","trend7":"7天趋势","trend30":"30天趋势",
        "opt_website":"网站","opt_cli":"命令行工具","opt_exec":"可执行程序",
        "cli_title":"命令行工具运行","cli_args":"参数","cli_run":"运行","cli_output":"输出"

    },
    "English":{
        "app_title":"Tool Manager","search":"Search tools...",
        "add_tool":"+ Add Tool","select_detail":"Select a tool to see details",
        "settings":"Settings","about":"About",
        "theme":"Theme","light":"Light","dark":"Dark","system":"System",
        "font_size":"Font Size","window_size":"Initial Window Size","language":"Language",
        "ok":"OK","cancel":"Cancel",
        "name":"Name","type":"Type","url":"URL","category":"Category",
        "path":"Executable","args":"Default Args","simple_description":"Description",
        "browse":"Browse…","import_doc":"Import Doc…",
        "add":"Add","edit":"Edit","delete":"Delete",
        "confirm_delete":"Confirm Delete","launch_error":"Launch Error",
        "restart_prompt":"Settings saved. Restart now to apply?",
        "recent_usage":"Recent Usage","today_top5":"Today Top5",
        "opt_py_cli": "Python CLI Tool",
        "opt_py_exec": "Python Executable",
        "trend7":"7‑day Trend","trend30":"30‑day Trend",
        "opt_website":"Website","opt_cli":"CLI","opt_exec":"Executable",
        "cli_title":"Run CLI Tool","cli_args":"Args","cli_run":"Run","cli_output":"Output"
    }
}

# 支持中文字体和负号
rcParams['font.sans-serif']=['Microsoft YaHei','Arial']
rcParams['axes.unicode_minus']=False

# JSON 读写
def load_json(path, default):
    try: return json.load(open(path, "r", encoding="utf-8"))
    except: return default.copy()

def save_json(path, data):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# 深色模式检测
def detect_windows_dark_mode():
    if not winreg: return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        val,_ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return val == 0
    except:
        return False

# 应用主题
def apply_theme(app, settings):
    font = app.font()
    font.setPointSize(settings.get("font_size", 10))
    app.setFont(font)
    theme = settings.get("theme", "System")
    dark = (theme=="Dark") or (theme=="System" and sys.platform.startswith("win") and detect_windows_dark_mode())
    qss = ""
    if dark:
        qss = """
        QWidget{background:#2e2e2e;color:#eaeaea;}
        QLineEdit,QTextEdit,QPlainTextEdit{background:#3c3c3c;color:#eaeaea;}
        QTreeWidget{background:#2e2e2e;color:#eaeaea;}
        QTreeWidget::item:selected{background:#505050;}
        QMenu{background:#3c3c3c;color:#eaeaea;}
        QTabBar::tab{background:#3c3c3c;color:#eaeaea;padding:6px;}
        QTabBar::tab:selected{background:#505050;}
        QPushButton{background:#3c3c3c;color:#eaeaea;border:1px solid #555;border-radius:2px;}
        QPushButton:hover{background:#505050;}
        """
    app.setStyleSheet(qss)

# 日志记录与统计
def log_usage(name):
    import datetime
    data = load_json(USAGE_LOG, [])
    data.append({"tool": name, "time": datetime.datetime.now().isoformat()})
    save_json(USAGE_LOG, data)

def compute_today_top5(data):
    import datetime
    from collections import Counter
    today = datetime.date.today().isoformat()
    cnt = Counter(e["tool"] for e in data if e["time"].startswith(today))
    return ([],[]) if not cnt else zip(*cnt.most_common(5))

def compute_trend(data, days):
    import datetime
    from collections import defaultdict
    c = defaultdict(int)
    for e in data:
        d = e["time"][:10]; dt = datetime.date.fromisoformat(d)
        if dt >= datetime.date.today() - datetime.timedelta(days=days-1):
            c[dt]+=1
    days_sorted = sorted(c)
    return days_sorted, [c[d] for d in days_sorted]

# 仪表盘
class Dashboard(QWidget):
    def __init__(self, L):
        super().__init__()
        layout = QVBoxLayout(self)
        usage = load_json(USAGE_LOG, [])

        # 今日 Top5
        tools, counts = compute_today_top5(usage)
        fig1 = Figure(figsize=(4,2), dpi=100); ax1 = fig1.add_subplot(111)
        ax1.bar(tools, counts); ax1.set_title(L["today_top5"]); ax1.grid(True, linestyle='--', alpha=0.5)
        fig1.tight_layout(); layout.addWidget(Canvas(fig1))

        # 7 天趋势
        days7, vals7 = compute_trend(usage, 7)
        labels7 = [d.strftime("%m-%d") for d in days7]
        fig2 = Figure(figsize=(4,2), dpi=100); ax2 = fig2.add_subplot(111)
        ax2.plot(labels7, vals7, marker="o"); ax2.set_title(L["trend7"]); ax2.grid(True, linestyle='--', alpha=0.5)
        fig2.tight_layout(); layout.addWidget(Canvas(fig2))

        # 30 天趋势
        days30, vals30 = compute_trend(usage, 30)
        labels30 = [d.strftime("%m-%d") for d in days30]
        fig3 = Figure(figsize=(4,2), dpi=100); ax3 = fig3.add_subplot(111)
        ax3.plot(labels30, vals30, marker="o"); ax3.set_title(L["trend30"]); ax3.grid(True, linestyle='--', alpha=0.5)
        fig3.tight_layout(); layout.addWidget(Canvas(fig3))

# 设置对话框
class SettingsDialog(QDialog):
    def __init__(self, settings, L):
        super().__init__(); self.settings = settings; self.L = L
        self.setWindowTitle(L["settings"]); self.resize(400,280)
        layout = QFormLayout(self)
        # 主题
        self.theme_cb = QComboBox(); self.theme_cb.addItems([L["light"],L["dark"],L["system"]])
        rev = {"Light":L["light"],"Dark":L["dark"],"System":L["system"]}
        self.theme_cb.setCurrentText(rev.get(settings.get("theme","System"), L["system"]))
        layout.addRow(L["theme"], self.theme_cb)
        # 字体
        self.font_spin = QSpinBox(); self.font_spin.setRange(6,32)
        self.font_spin.setValue(settings.get("font_size",10)); layout.addRow(L["font_size"], self.font_spin)
        # 窗口大小
        h=QHBoxLayout(); self.w_spin,self.h_spin=QSpinBox(),QSpinBox()
        self.w_spin.setRange(400,5000); self.h_spin.setRange(300,3000)
        self.w_spin.setValue(settings.get("window_width",1800))
        self.h_spin.setValue(settings.get("window_height",1200))
        h.addWidget(QLabel("W:")); h.addWidget(self.w_spin)
        h.addWidget(QLabel("H:")); h.addWidget(self.h_spin)
        layout.addRow(L["window_size"], h)
        # 语言
        self.lang_cb = QComboBox(); self.lang_cb.addItems(list(I18N.keys()))
        self.lang_cb.setCurrentText(settings.get("language","中文")); layout.addRow(L["language"], self.lang_cb)
        # ← 新增：Python 解释器路径
        self.python_path_edit = QLineEdit(settings.get("python_path", "python"))
        layout.addRow("Python 解释器路径", self.python_path_edit)
        # 按钮
        bb = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(L["ok"]); bb.button(QDialogButtonBox.Cancel).setText(L["cancel"])
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); layout.addWidget(bb)

    def get_settings(self):
        rev = {self.L["light"]:"Light", self.L["dark"]:"Dark", self.L["system"]:"System"}
        return {
            "theme": rev[self.theme_cb.currentText()],
            "font_size": self.font_spin.value(),
            "window_width": self.w_spin.value(),
            "window_height": self.h_spin.value(),
            "language": self.lang_cb.currentText(),
            "python_path": self.python_path_edit.text().strip()   # 新增
        }

# 命令行工具对话框，实时输出
class CommandLineDialog(QDialog):
    def __init__(self, exe, script, default_args, L):
        super().__init__(); self.L=L
        self.script = script        # ← 新增：保存脚本路径
        self.setWindowTitle(L["cli_title"]); self.resize(600,400)
        layout = QVBoxLayout(self)
        # 参数
        h = QHBoxLayout()
        self.arg_edit = QLineEdit(" ".join(default_args))
        self.arg_edit.setPlaceholderText(L["cli_args"])
        h.addWidget(self.arg_edit)
        run_btn = QPushButton(L["cli_run"]); run_btn.clicked.connect(self.run_cmd)
        h.addWidget(run_btn)
        layout.addLayout(h)
        # 输出
        self.out_view = QPlainTextEdit(); self.out_view.setReadOnly(True)
        layout.addWidget(self.out_view)
        # QProcess
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.on_ready_read)
        self.process.finished.connect(self.on_finished)
        self.exe = exe

    def run_cmd(self):
        if self.process.state() != QProcess.NotRunning:
            self.process.kill()
            self.process.waitForFinished()
            self.out_view.appendPlainText("\n--- 进程被中断 ---\n")
        self.out_view.clear()
        parts = self.arg_edit.text().split()
        # 真正的启动参数：先插入 script，再加上用户输入的 parts
        args = ([self.script] if self.script else []) + parts
        self.process.start(self.exe, args)

    def on_ready_read(self):
        data = self.process.readAllStandardOutput().data().decode(errors="ignore")
        self.out_view.appendPlainText(data)

    def on_finished(self, exitCode, exitStatus):
        self.out_view.appendPlainText(f"\n--- 进程结束，退出码: {exitCode} ---\n")

# 添加／编辑工具对话框
class AddToolDialog(QDialog):
    def __init__(self, L, tool=None):
        super().__init__()
        self.L = L
        self.tool = tool

        self.setWindowTitle(L["add_tool"] if not tool else L["edit"])
        self.resize(600, 800)

        fmt = QFormLayout(self)

        # 1) 类型下拉
        self.type_cb = QComboBox()
        self.type_cb.addItems([
            L["opt_website"],
            L["opt_cli"],
            L["opt_exec"],
            L["opt_py_cli"],  # 新增
            L["opt_py_exec"],  # 新增
        ])
        fmt.addRow(L["type"], self.type_cb)

        # 2) 名称、URL、分类、路径、参数、文档、说明  —— 先创建好所有控件
        self.name = QLineEdit();           fmt.addRow(L["name"], self.name)
        self.url  = QLineEdit();           fmt.addRow(L["url"], self.url)

        self.cat  = QComboBox();           self.cat.setEditable(True)
        self.cat.addItems(["", "测试工具", "开发工具", "其他"])
        fmt.addRow(L["category"], self.cat)

        self.path = QLineEdit();           fmt.addRow(L["path"], self.path)
        fmt.addWidget(QPushButton(L["browse"], clicked=self.browse_file))

        self.args = QLineEdit();           fmt.addRow(L["args"], self.args)

        self.doc  = QLineEdit();           fmt.addRow("说明文档", self.doc)
        fmt.addWidget(QPushButton(L["browse"], clicked=self.browse_doc))

        self.desc = QTextEdit();           self.desc.setFixedHeight(120)
        fmt.addRow(L["simple_description"], self.desc)

        # 3) OK / Cancel 按钮
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(L["ok"])
        bb.button(QDialogButtonBox.Cancel).setText(L["cancel"])
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        fmt.addWidget(bb)

        # 4) 类型变更联动：放在所有控件创建之后
        self.type_cb.currentTextChanged.connect(self.update_fields)

        # 5) 如果是编辑模式，先恢复类型，再恢复其它字段
        if tool:
            # 恢复类型
            self.type_cb.setCurrentText(tool["type"])
            # 恢复其它字段
            self.name.setText(tool["name"])
            self.url.setText(tool.get("url", ""))
            self.cat.setCurrentText(tool.get("category", ""))
            self.path.setText(tool.get("path", ""))
            self.args.setText(tool.get("args", ""))
            self.doc.setText(tool.get("doc_path", ""))
            self.desc.setPlainText(tool.get("description", ""))

        # 6) 最后根据最终的 type_cb 文本设置各控件可用性
        self.update_fields(self.type_cb.currentText())

    def update_fields(self, t):
        is_ws = (t == self.L["opt_website"])
        is_cli = (t == self.L["opt_cli"])
        is_exec = (t == self.L["opt_exec"])
        is_py_cli = (t == self.L["opt_py_cli"])  # 新增：命令行 Python 工具
        is_py_exec = (t == self.L["opt_py_exec"])  # 新增：可执行 Python 工具

        # URL 仅网站时启用
        self.url.setEnabled(is_ws)

        # 路径在 CLI、EXE、命令行Python、可执行Python 时启用
        self.path.setEnabled(is_cli or is_exec or is_py_cli or is_py_exec)

        # 参数仅在 CLI 或 命令行Python 时启用
        self.args.setEnabled(is_cli or is_py_cli)

        # 文档与说明始终启用
        self.doc.setEnabled(True)
        self.desc.setEnabled(True)

    def browse_file(self):
        f, _ = QFileDialog.getOpenFileName(self, self.L["browse"], "", "*.*")
        if f:
            self.path.setText(f)

    def browse_doc(self):
        f, _ = QFileDialog.getOpenFileName(self, self.L["browse"], "", "*.md;;*.txt;;*.pdf")
        if f:
            self.doc.setText(f)

    def get_tool_info(self):
        return {
            "name":        self.name.text().strip(),
            "type":        self.type_cb.currentText(),
            "url":         self.url.text().strip(),
            "category":    self.cat.currentText().strip(),
            "path":        self.path.text().strip(),
            "args":        self.args.text().strip(),
            "doc_path":    self.doc.text().strip(),
            "description": self.desc.toPlainText().strip()
        }


# 主界面
class ToolManager(QWidget):
    def __init__(self):
        super().__init__()
        # ← 新增：在窗体创建时设置窗口图标
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        apply_theme(QApplication.instance() or QApplication(sys.argv), self.settings)
        self.L = I18N[self.settings["language"]]
        self.setWindowTitle(self.L["app_title"])
        self.resize(self.settings["window_width"], self.settings["window_height"])
        self.tools_data = load_json(TOOLS_FILE, [])
        self.init_ui()

    def init_ui(self):
        main = QVBoxLayout(self)
        tabs = QTabWidget()
        # 管理页
        mgr = QWidget(); ml = QVBoxLayout(mgr)
        hb = QHBoxLayout()
        tb = QToolButton(); tb.setText("☰"); tb.setPopupMode(QToolButton.MenuButtonPopup)
        tb.clicked.connect(self.toggle_sidebar)
        menu = QMenu(tb); menu.addAction(self.L["settings"], self.open_settings)
        menu.addAction(self.L["about"], self.open_about); tb.setMenu(menu)
        hb.addWidget(tb); hb.addWidget(QLabel(self.L["app_title"])); hb.addStretch()
        self.search = QLineEdit(); self.search.setPlaceholderText(self.L["search"])
        self.search.textChanged.connect(self.on_search); hb.addWidget(self.search)
        ml.addLayout(hb)
        # 内容区
        self.splitter = QSplitter(Qt.Horizontal)
        # 左侧
        left = QWidget(); ll = QVBoxLayout(left)
        ll.addWidget(QPushButton(self.L["add_tool"], clicked=self.show_add))
        self.tree = QTreeWidget(); self.tree.setHeaderLabels([self.L["name"], ""])
        self.tree.setColumnHidden(1, True)
        self.tree.itemClicked.connect(self.on_item)
        self.tree.itemDoubleClicked.connect(self.on_double)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_context)
        ll.addWidget(self.tree); self.splitter.addWidget(left)
        # 右侧
        right = QWidget(); rl = QVBoxLayout(right)
        self.detail_title = QLabel(self.L["select_detail"]); self.detail_title.setStyleSheet("font-size:20px;")
        self.detail_text = QTextEdit(); self.detail_text.setReadOnly(True)
        rl.addWidget(self.detail_title); rl.addWidget(self.detail_text); self.splitter.addWidget(right)
        ml.addWidget(self.splitter)
        # Tabs
        tabs.addTab(mgr, self.L["app_title"])
        tabs.addTab(Dashboard(self.L), self.L["recent_usage"])
        main.addWidget(tabs)
        self.refresh_tree()

    # 回调 & 方法
    def toggle_sidebar(self):
        vis = self.tree.isVisible()
        self.tree.setVisible(not vis)
        self.splitter.setSizes([0, self.width()] if vis else [300, self.width()-300])

    def on_search(self, text):
        k = text.lower()
        fl = [t for t in self.tools_data if k in t["name"].lower() or k in t["category"].lower()]
        self.refresh_tree(fl)

    def on_item(self, it, _):
        info = it.data(1, Qt.DisplayRole)
        if not info: return
        t = json.loads(info)
        md = f"# {t['name']}\n\n- **{self.L['category']}**: {t['category']}\n\n{t.get('description','')}"
        self.detail_title.setText(t["name"])
        self.detail_text.setHtml(markdown.markdown(md, extensions=["fenced_code","tables"]))

    def on_double(self, it, _):
        info = it.data(1, Qt.DisplayRole)
        if not info:
            return
        t = json.loads(info)
        log_usage(t["name"])
        typ = t["type"]
        exe = t.get("path", "")
        default_args = t.get("args", "").split()
        url = t.get("url", "")
        doc = t.get("doc_path", "")

        # 1. 网站类型
        if typ == self.L["opt_website"] and url:
            webbrowser.open(url)
            if doc and os.path.isfile(doc):
                os.startfile(doc)
            return

        # 2. 普通命令行工具
        if typ == self.L["opt_cli"] and exe and os.path.isfile(exe):
            # exe 就是可执行路径，script 设为 None
            self.cli_dialog = CommandLineDialog(exe, None, default_args, self.L)
            self.cli_dialog.show()
            if doc and os.path.isfile(doc):
                os.startfile(doc)
            return

        # 3. 可执行程序
        if typ == self.L["opt_exec"] and exe and os.path.isfile(exe):
            try:
                os.startfile(exe)
            except Exception as e:
                QMessageBox.warning(self, self.L["launch_error"], str(e))
            if doc and os.path.isfile(doc):
                os.startfile(doc)
            return

        # 命令行 Python 工具
        if typ == self.L["opt_py_cli"] and exe and os.path.isfile(exe):
            python = self.settings.get("python_path", "python")
            # exe 是 .py 脚本路径，传给 script
            self.cli_dialog = CommandLineDialog(python, exe, default_args, self.L)
            self.cli_dialog.show()
            if doc and os.path.isfile(doc):
                os.startfile(doc)
            return

        # 可执行 Python 工具（GUI 脚本或打包后的 .exe）
        if typ == self.L["opt_py_exec"] and exe and os.path.isfile(exe):
            python = self.settings.get("python_path", "python")
            try:
                # script 放在参数列表里同理，也可以直接双击 .exe
                QProcess.startDetached(python, [exe] + default_args)
            except Exception as e:
                QMessageBox.warning(self, self.L["launch_error"], str(e))
            if doc and os.path.isfile(doc):
                os.startfile(doc)
            return

    def show_add(self):
        dlg = AddToolDialog(self.L)
        if dlg.exec_():
            self.tools_data.append(dlg.get_tool_info())
            save_json(TOOLS_FILE, self.tools_data)
            self.refresh_tree()

    def on_context(self, pos):
        it = self.tree.itemAt(pos)
        if not it or not it.data(1, Qt.DisplayRole): return
        menu = QMenu(self)
        menu.addAction(self.L["edit"], lambda: self.edit_tool(it))
        menu.addAction(self.L["delete"], lambda: self.delete_tool(it))
        menu.exec_(self.tree.mapToGlobal(pos))

    def delete_tool(self, it):
        t = json.loads(it.data(1, Qt.DisplayRole))
        if QMessageBox.question(self, self.L["confirm_delete"], f"{t['name']}?") != QMessageBox.Yes:
            return
        self.tools_data = [x for x in self.tools_data if not(x["name"]==t["name"] and x["category"]==t["category"])]
        save_json(TOOLS_FILE, self.tools_data)
        self.refresh_tree()

    def edit_tool(self, it):
        t = json.loads(it.data(1, Qt.DisplayRole))
        dlg = AddToolDialog(self.L, tool=t)
        if dlg.exec_():
            new = dlg.get_tool_info()
            idx = self.tools_data.index(t)
            self.tools_data[idx] = new
            save_json(TOOLS_FILE, self.tools_data)
            self.refresh_tree()

    def open_settings(self):
        dlg = SettingsDialog(self.settings, self.L)
        if dlg.exec_():
            new = dlg.get_settings()
            save_json(SETTINGS_FILE, new)
            QMessageBox.information(self, self.L["settings"], self.L["restart_prompt"])
            apply_theme(QApplication.instance(), new)
            self.settings = new

    def open_about(self):
        # 中文环境
        if self.settings.get("language", "中文") == "中文":
            text = "版本 1.0\n作者：zyf\nPowered by PyQt5"
        else:
            # English environment
            text = "Version 1.0\nAuthor: zyf\nPowered by PyQt5"
        QMessageBox.information(self, self.L["about"], text)

    def refresh_tree(self, filtered=None):
        self.tree.clear()
        groups = {}
        for t in (filtered or self.tools_data):
            groups.setdefault(t["category"], []).append(t)
        for cat, tools in groups.items():
            ci = QTreeWidgetItem([cat, ""])
            ci.setFirstColumnSpanned(True)
            self.tree.addTopLevelItem(ci)
            for t in tools:
                ni = QTreeWidgetItem([t["name"], json.dumps(t)])
                ci.addChild(ni)
        self.tree.expandAll()

if __name__=='__main__':
    app = QApplication(sys.argv)
    # ← 可选：全局设置 App 图标（有些平台任务栏会优先取这里的）
    icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    win = ToolManager()
    win.show()
    sys.exit(app.exec_())
