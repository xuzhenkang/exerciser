import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import random
import os
from datetime import datetime
import sys

# 确保Python 3.6兼容性
if sys.version_info < (3, 6):
    raise Exception("本软件需要Python 3.6或更高版本运行")


class ExamSoftware:
    def __init__(self, root):
        """初始化刷题软件"""
        self.root = root
        self.root.title("题刷刷")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)

        # 设置中文字体支持
        self.font_family = "SimHei"
        self.style = ttk.Style()

        # 颜色方案 - 美化界面
        self.colors = {
            "bg": "#f5f7fa",  # 背景色
            "card": "#ffffff",  # 卡片背景
            "primary": "#4285f4",  # 主色调-蓝色
            "success": "#34a853",  # 成功-绿色
            "warning": "#fbbc05",  # 警告-黄色
            "danger": "#ea4335",  # 危险-红色
            "text": "#202124",  # 文本颜色
            "text_light": "#5f6368",  # 次要文本
            "border": "#dadce0",  # 边框颜色
            "hover": "#e8f0fe"  # 悬停效果
        }

        self.setup_styles()

        # 数据初始化
        self.current_index = 0  # 当前题目索引
        self.last_practice_positions = {}  # 存储每种练习模式的最后位置
        self.question_bank = []  # 题库
        self.current_questions = []  # 当前练习的题目
        self.current_index = 0  # 当前题目索引
        self.user_answers = {}  # 用户答案
        self.wrong_questions = []  # 错题集
        self.mode = ""  # 练习模式
        self.exam_results = {}  # 考试结果
        self.current_bank_id = None  # 当前题库ID
        self.current_bank_name = ""  # 当前题库名称
        self.question_index_map = {}  # 用于映射进度框位置到题目索引
        self.exam_config = {  # 存储上次考试配置
            "single": 10,
            "multiple": 5,
            "judge": 10
        }

        # 初始化数据库
        self.init_database()

        # 界面组件缓存
        self.progress_frames = {}  # 缓存进度框组件
        self.content_frame = None  # 内容区域框架
        self.progress_canvas = None  # 进度区画布
        self.progress_scrollable_frame = None  # 进度区可滚动框架

        # 加载错题集
        self.load_wrong_questions()

        # 尝试加载上次使用的题库
        self.load_last_used_bank()

        # 创建主界面
        self.create_main_interface()

    def setup_styles(self):
        """设置界面样式"""
        # 配置ttk样式
        self.style.configure("TButton", font=(self.font_family, 10))
        self.style.configure("TLabel", font=(self.font_family, 10))

        # 自定义样式
        self.style.configure("Header.TLabel", font=(self.font_family, 16, "bold"))
        self.style.configure("Title.TLabel", font=(self.font_family, 24, "bold"))
        self.style.configure("Question.TLabel", font=(self.font_family, 12))
        self.style.configure("Option.TRadiobutton", font=(self.font_family, 11))
        self.style.configure("Option.TCheckbutton", font=(self.font_family, 11))
        self.style.configure("Status.TLabel", font=(self.font_family, 10), foreground="gray")

        # 按钮样式美化
        self.style.configure("Primary.TButton",
                             background=self.colors["primary"],
                             foreground="white",
                             font=(self.font_family, 10, "bold"))
        self.style.map("Primary.TButton",
                       background=[("active", "#3367d6")])

    def init_database(self):
        """初始化SQLite数据库"""
        try:
            # 连接数据库，不存在则创建
            self.conn = sqlite3.connect('exam_software.db')
            self.cursor = self.conn.cursor()

            # 启用外键约束
            self.cursor.execute("PRAGMA foreign_keys = ON")

            # 创建题库表
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_banks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_last_used INTEGER DEFAULT 0
            )
            ''')

            # 创建题目表
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                is_subquestion INTEGER DEFAULT 0,
                options TEXT,
                difficulty TEXT,
                analysis TEXT,
                answer TEXT NOT NULL,
                score REAL DEFAULT 0,
                FOREIGN KEY (bank_id) REFERENCES question_banks (id) ON DELETE CASCADE
            )
            ''')

            # 创建答题进度表
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id INTEGER NOT NULL,
                mode TEXT NOT NULL,
                question_id INTEGER NOT NULL,
                user_answer TEXT,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bank_id) REFERENCES question_banks (id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
                UNIQUE(bank_id, mode, question_id)
            )
            ''')

            # 创建题目顺序表
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id INTEGER NOT NULL,
                mode TEXT NOT NULL,
                position INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                FOREIGN KEY (bank_id) REFERENCES question_banks (id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
                UNIQUE(bank_id, mode, position)
            )
            ''')

            # 创建错题集表
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS wrong_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                user_answer TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bank_id) REFERENCES question_banks (id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
                UNIQUE(bank_id, question_id)
            )
            ''')

            # 创建配置表
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL
            )
            ''')

            # 加载考试配置
            self.load_exam_config()

            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"初始化数据库失败: {str(e)}")
            # 尝试关闭连接
            if hasattr(self, 'conn'):
                self.conn.close()
            # 退出程序
            sys.exit(1)

    def load_exam_config(self):
        """加载上次考试配置"""
        try:
            self.cursor.execute(
                "SELECT key, value FROM config WHERE key IN ('single_count', 'multiple_count', 'judge_count')")
            results = self.cursor.fetchall()

            for key, value in results:
                if key == 'single_count':
                    self.exam_config['single'] = int(value)
                elif key == 'multiple_count':
                    self.exam_config['multiple'] = int(value)
                elif key == 'judge_count':
                    self.exam_config['judge'] = int(value)
        except sqlite3.Error as e:
            print(f"加载考试配置失败: {str(e)}")

    def save_exam_config(self):
        """保存考试配置"""
        try:
            # 保存单选题数量
            self.cursor.execute('''
            INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)
            ''', ('single_count', str(self.exam_config['single'])))

            # 保存多选题数量
            self.cursor.execute('''
            INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)
            ''', ('multiple_count', str(self.exam_config['multiple'])))

            # 保存判断题数量
            self.cursor.execute('''
            INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)
            ''', ('judge_count', str(self.exam_config['judge'])))

            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"保存考试配置失败: {str(e)}")

    def load_last_used_bank(self):
        """加载上次使用的题库"""
        try:
            self.cursor.execute("SELECT id, name FROM question_banks WHERE is_last_used = 1 LIMIT 1")
            result = self.cursor.fetchone()

            if result:
                self.current_bank_id = result[0]
                self.current_bank_name = result[1]
                self.load_question_bank()
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"加载上次使用的题库失败: {str(e)}")

    def set_last_used_bank(self, bank_id):
        """设置指定题库为上次使用的题库"""
        try:
            # 先清除所有上次使用标记
            self.cursor.execute("UPDATE question_banks SET is_last_used = 0")

            # 设置当前题库为上次使用
            self.cursor.execute(
                "UPDATE question_banks SET is_last_used = 1 WHERE id = ?",
                (bank_id,)
            )

            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"设置上次使用的题库失败: {str(e)}")

    def create_main_interface(self):
        """创建主界面 - 美化版本"""
        # 清空当前界面
        for widget in self.root.winfo_children():
            widget.destroy()

        # 设置背景颜色
        self.root.configure(bg=self.colors["bg"])

        # 顶部标题区
        header_frame = tk.Frame(self.root, bg=self.colors["primary"], height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        title_label = ttk.Label(
            header_frame,
            text="题刷刷",
            style="Title.TLabel",
            background=self.colors["primary"],
            foreground="white"
        )
        title_label.pack(pady=10)

        # 主内容区
        content_frame = tk.Frame(self.root, bg=self.colors["bg"])
        content_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=30)

        # 功能卡片
        card_frame = tk.Frame(
            content_frame,
            bg=self.colors["card"],
            bd=0,
            relief=tk.RAISED,
            padx=40,
            pady=30
        )
        card_frame.pack(expand=True)

        # 添加卡片阴影效果
        card_frame.configure(highlightbackground=self.colors["border"], highlightthickness=1)

        # 功能按钮区域
        button_frame = tk.Frame(card_frame, bg=self.colors["card"])
        button_frame.pack(expand=True, pady=20)

        # 按钮样式 - 美化版
        button_style = {
            "font": (self.font_family, 12),
            "width": 22,
            "height": 2,
            "relief": tk.FLAT,
            "bd": 0,
            "bg": self.colors["primary"],
            "fg": "white",
            "activebackground": "#3367d6",
            "cursor": "hand2"
        }

        # 导入题库按钮
        import_btn = tk.Button(
            button_frame,
            text="从Excel导入题库",
            command=self.import_from_excel, **button_style
        )
        import_btn.grid(row=0, column=0, columnspan=2, padx=30, pady=15)
        import_btn.bind("<Enter>", lambda e: e.widget.configure(bg="#3367d6"))
        import_btn.bind("<Leave>", lambda e: e.widget.configure(bg=self.colors["primary"]))

        # 顺序练习按钮 - 不同样式
        seq_style = button_style.copy()
        seq_style["bg"] = "#f1f3f4"
        seq_style["fg"] = self.colors["text"]
        seq_style["activebackground"] = self.colors["hover"]

        seq_btn = tk.Button(
            button_frame,
            text="顺序练习",
            command=lambda: self.start_practice("sequence"),
            state=tk.NORMAL if self.question_bank else tk.DISABLED,
            **seq_style
        )
        seq_btn.grid(row=1, column=0, padx=30, pady=15)
        seq_btn.bind("<Enter>",
                     lambda e: e.widget.configure(bg=self.colors["hover"]) if e.widget["state"] == tk.NORMAL else None)
        seq_btn.bind("<Leave>", lambda e: e.widget.configure(bg="#f1f3f4") if e.widget["state"] == tk.NORMAL else None)

        # 随机练习按钮
        rand_btn = tk.Button(
            button_frame,
            text="随机练习",
            command=lambda: self.start_practice("random"),
            state=tk.NORMAL if self.question_bank else tk.DISABLED, **seq_style
        )
        rand_btn.grid(row=1, column=1, padx=30, pady=15)
        rand_btn.bind("<Enter>",
                      lambda e: e.widget.configure(bg=self.colors["hover"]) if e.widget["state"] == tk.NORMAL else None)
        rand_btn.bind("<Leave>", lambda e: e.widget.configure(bg="#f1f3f4") if e.widget["state"] == tk.NORMAL else None)

        # 组合试卷按钮
        exam_btn = tk.Button(
            button_frame,
            text="组合试卷",
            command=self.create_exam,
            state=tk.NORMAL if self.question_bank else tk.DISABLED, **seq_style
        )
        exam_btn.grid(row=2, column=0, padx=30, pady=15)
        exam_btn.bind("<Enter>",
                      lambda e: e.widget.configure(bg=self.colors["hover"]) if e.widget["state"] == tk.NORMAL else None)
        exam_btn.bind("<Leave>", lambda e: e.widget.configure(bg="#f1f3f4") if e.widget["state"] == tk.NORMAL else None)

        # 错题集按钮
        wrong_btn = tk.Button(
            button_frame,
            text="查看错题集",
            command=self.view_wrong_questions,
            state=tk.NORMAL if self.question_bank else tk.DISABLED, **seq_style
        )
        wrong_btn.grid(row=2, column=1, padx=30, pady=15)
        wrong_btn.bind("<Enter>", lambda e: e.widget.configure(bg=self.colors["hover"]) if e.widget[
                                                                                               "state"] == tk.NORMAL else None)
        wrong_btn.bind("<Leave>",
                       lambda e: e.widget.configure(bg="#f1f3f4") if e.widget["state"] == tk.NORMAL else None)

        # 状态标签
        self.status_label = ttk.Label(
            self.root,
            text="请先从Excel导入题库" if not self.question_bank else
            f"已加载题库: {self.current_bank_name}，共 {len(self.question_bank)} 道题",
            style="Status.TLabel",
            background=self.colors["bg"]
        )
        self.status_label.pack(side=tk.BOTTOM, pady=20)

    def import_from_excel(self):
        """从Excel导入题库"""
        try:
            import xlrd  # 延迟导入，仅在需要时加载
            if xlrd.__version__ > "1.2.0":
                raise ImportError("xlrd版本过高，不支持xlsx格式，请安装1.2.0版本")
        except ImportError as e:
            messagebox.showerror("错误", f"请安装xlrd库以导入Excel文件：\npip install xlrd==1.2.0\n{str(e)}")
            return

        file_path = filedialog.askopenfilename(
            title="选择Excel题库文件",
            filetypes=[("Excel files", "*.xls;*.xlsx")]
        )

        if not file_path:
            return

        # 获取文件名作为默认题库名
        default_name = os.path.splitext(os.path.basename(file_path))[0]

        # 询问题库名称 - 美化对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("导入题库")
        dialog.geometry("350x180")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.colors["bg"])

        # 添加标题栏
        header = tk.Frame(dialog, bg=self.colors["primary"], height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        ttk.Label(
            header,
            text="导入题库",
            font=(self.font_family, 12, "bold"),
            background=self.colors["primary"],
            foreground="white"
        ).pack(pady=8)

        ttk.Label(
            dialog,
            text="请输入题库名称:",
            font=(self.font_family, 10),
            background=self.colors["bg"]
        ).pack(pady=15)

        name_var = tk.StringVar(value=default_name)
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30, font=(self.font_family, 11))
        name_entry.pack(pady=5)
        name_entry.select_range(0, tk.END)
        name_entry.focus()

        def confirm_import():
            bank_name = name_var.get().strip()
            if not bank_name:
                messagebox.showwarning("警告", "请输入题库名称")
                return

            try:
                # 读取Excel文件
                workbook = xlrd.open_workbook(file_path)
                sheet = workbook.sheet_by_index(0)

                # 创建新题库
                self.cursor.execute(
                    "INSERT INTO question_banks (name, created_at, updated_at) VALUES (?, ?, ?)",
                    (bank_name, datetime.now(), datetime.now())
                )
                bank_id = self.cursor.lastrowid

                # 导入题目
                success_count = 0
                for i in range(1, sheet.nrows):  # 跳过表头
                    try:
                        row = sheet.row_values(i)
                        if not row[0]:  # 跳过空行
                            continue

                        # 解析每一行数据
                        question = {
                            "bank_id": bank_id,
                            "content": row[0],  # 试题题干
                            "type": row[1] if len(row) > 1 else "单选",  # 试题类型
                            "is_subquestion": 1 if (len(row) > 2 and str(row[2]).lower() in ["true", "1", "是"]) else 0,
                            "options": "|".join(str(opt).strip() for opt in row[3].split('|')) if (
                                    len(row) > 3 and row[3]) else "",
                            "difficulty": row[4] if len(row) > 4 else "中等",
                            "analysis": row[5] if len(row) > 5 else "",
                            "answer": row[6] if len(row) > 6 else "",
                            "score": float(row[7]) if (len(row) > 7 and row[7]) else 0
                        }

                        # 处理判断题选项
                        if question["type"] == "判断" and not question["options"]:
                            question["options"] = "正确|错误"

                        # 插入数据库
                        self.cursor.execute('''
                        INSERT INTO questions 
                        (bank_id, content, type, is_subquestion, options, difficulty, analysis, answer, score)
                        VALUES (:bank_id, :content, :type, :is_subquestion, :options, :difficulty, :analysis, :answer, :score)
                        ''', question)

                        success_count += 1
                    except Exception as e:
                        print(f"导入第{i + 1}行失败: {str(e)}")
                        continue

                self.conn.commit()

                # 设置为上次使用的题库
                self.set_last_used_bank(bank_id)

                # 刷新题库
                self.current_bank_id = bank_id
                self.current_bank_name = bank_name
                self.load_question_bank()
                self.create_main_interface()

                messagebox.showinfo("成功", f"题库导入完成，共导入 {success_count} 道题")
                dialog.destroy()

            except sqlite3.Error as e:
                self.conn.rollback()
                messagebox.showerror("数据库错误", f"导入失败: {str(e)}")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {str(e)}")

        btn_frame = tk.Frame(dialog, bg=self.colors["bg"])
        btn_frame.pack(pady=15)

        tk.Button(
            btn_frame,
            text="确定",
            command=confirm_import,
            width=10,
            bg=self.colors["primary"],
            foreground="white",
            activebackground="#3367d6",
            relief=tk.FLAT
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame,
            text="取消",
            command=dialog.destroy,
            width=10,
            bg="#f1f3f4",
            foreground=self.colors["text"],
            activebackground=self.colors["hover"],
            relief=tk.FLAT
        ).pack(side=tk.LEFT, padx=5)

    def load_question_bank(self):
        """从数据库加载题库"""
        if not self.current_bank_id:
            return

        self.question_bank = []
        try:
            self.cursor.execute(
                "SELECT id, content, type, is_subquestion, options, difficulty, analysis, answer, score "
                "FROM questions WHERE bank_id = ? ORDER BY id",
                (self.current_bank_id,)
            )

            for row in self.cursor.fetchall():
                question = {
                    "id": row[0],
                    "content": row[1],
                    "type": row[2],
                    "is_subquestion": row[3],
                    "options": row[4].split('|') if row[4] else [],
                    "difficulty": row[5],
                    "analysis": row[6],
                    "answer": row[7],
                    "score": row[8]
                }

                # 处理判断题选项
                if question["type"] == "判断" and not question["options"]:
                    question["options"] = ["正确", "错误"]

                self.question_bank.append(question)
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"加载题库失败: {str(e)}")
            self.question_bank = []

    def start_practice(self, mode):
        """开始练习"""
        if not self.question_bank:
            messagebox.showwarning("警告", "请先加载题库")
            return

        self.mode = mode
        self.current_index = 0

        # 从数据库中加载用户答案
        self.user_answers = {}
        try:
            self.cursor.execute(
                "SELECT question_id, user_answer FROM progress "
                "WHERE bank_id = ? AND mode = ?",
                (self.current_bank_id, mode)
            )

            for row in self.cursor.fetchall():
                self.user_answers[row[0]] = row[1]
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"加载答题进度失败: {str(e)}")
            self.user_answers = {}

        # 根据模式选择题目顺序
        if mode == "sequence":
            # 按题型分组排序：单选题、多选题、判断题
            single_questions = [q for q in self.question_bank if q["type"] == "单选"]
            multiple_questions = [q for q in self.question_bank if q["type"] == "多选"]
            judge_questions = [q for q in self.question_bank if q["type"] == "判断"]

            # 按ID排序每种题型内的题目
            single_questions.sort(key=lambda q: q["id"])
            multiple_questions.sort(key=lambda q: q["id"])
            judge_questions.sort(key=lambda q: q["id"])

            # 按顺序组合题目
            self.current_questions = single_questions + multiple_questions + judge_questions

            # 保存题目顺序
            self.save_question_order(mode)

            # 加载上次练习位置
            try:
                self.cursor.execute(
                    "SELECT value FROM config WHERE key = ?",
                    (f"last_position_{mode}_{self.current_bank_id}",)
                )
                result = self.cursor.fetchone()
                if result:
                    last_index = int(result[0])
                    if 0 <= last_index < len(self.current_questions):
                        self.current_index = last_index
            except sqlite3.Error as e:
                print(f"加载上次练习位置失败: {str(e)}")

        elif mode == "random":
            # 检查是否已有保存的随机顺序
            try:
                self.cursor.execute(
                    "SELECT question_id FROM question_orders "
                    "WHERE bank_id = ? AND mode = ? ORDER BY position",
                    (self.current_bank_id, mode)
                )

                saved_order = [row[0] for row in self.cursor.fetchall()]

                # 检查是否是第一次使用随机练习
                is_first_time = not (saved_order and len(saved_order) == len(self.question_bank))

                need_shuffle = True
                if not is_first_time:
                    # 如果不是第一次，询问用户是否需要重新打乱顺序
                    result = messagebox.askyesno("随机练习",
                                                 "是否需要重新打乱题目顺序？\n选择“是”将重新打乱题目顺序，选择“否”将保持上次的顺序。")
                    need_shuffle = result

                if need_shuffle or is_first_time:
                    # 按题型分组并分别随机排序
                    single_questions = [q for q in self.question_bank if q["type"] == "单选"]
                    multiple_questions = [q for q in self.question_bank if q["type"] == "多选"]
                    judge_questions = [q for q in self.question_bank if q["type"] == "判断"]

                    # 分别打乱各题型
                    random.shuffle(single_questions)
                    random.shuffle(multiple_questions)
                    random.shuffle(judge_questions)

                    # 按顺序组合
                    self.current_questions = single_questions + multiple_questions + judge_questions
                    self.save_question_order(mode)
                    # 如果是重新打乱顺序，则从第一题开始
                    self.current_index = 0
                else:
                    # 使用保存的顺序
                    self.current_questions = []
                    for qid in saved_order:
                        for q in self.question_bank:
                            if q["id"] == qid:
                                self.current_questions.append(q)
                                break
            except sqlite3.Error as e:
                messagebox.showerror("数据库错误", f"加载题目顺序失败: {str(e)}")
                # 如果出错，使用默认随机排序
                single_questions = [q for q in self.question_bank if q["type"] == "单选"]
                multiple_questions = [q for q in self.question_bank if q["type"] == "多选"]
                judge_questions = [q for q in self.question_bank if q["type"] == "判断"]

                random.shuffle(single_questions)
                random.shuffle(multiple_questions)
                random.shuffle(judge_questions)

                self.current_questions = single_questions + multiple_questions + judge_questions
                self.save_question_order(mode)

            # 加载上次练习位置（仅在使用保存的顺序时）
            if not is_first_time and not need_shuffle:
                try:
                    self.cursor.execute(
                        "SELECT value FROM config WHERE key = ?",
                        (f"last_position_{mode}_{self.current_bank_id}",)
                    )
                    result = self.cursor.fetchone()
                    if result:
                        last_index = int(result[0])
                        if 0 <= last_index < len(self.current_questions):
                            self.current_index = last_index
                except sqlite3.Error as e:
                    print(f"加载上次练习位置失败: {str(e)}")

        # 显示题目
        self.init_question_interface()
        self.update_question_display()
        self.update_progress_display()

    def save_question_order(self, mode):
        """保存题目的顺序到数据库"""
        if not self.current_bank_id or not self.current_questions:
            return

        try:
            # 先删除该模式下已有的顺序
            self.cursor.execute(
                "DELETE FROM question_orders WHERE bank_id = ? AND mode = ?",
                (self.current_bank_id, mode)
            )

            # 插入新的顺序
            for position, question in enumerate(self.current_questions):
                self.cursor.execute(
                    "INSERT INTO question_orders (bank_id, mode, position, question_id) "
                    "VALUES (?, ?, ?, ?)",
                    (self.current_bank_id, mode, position, question["id"])
                )

            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            messagebox.showerror("数据库错误", f"保存题目顺序失败: {str(e)}")

    def save_current_position(self):
        """保存当前练习位置"""
        if not self.current_bank_id or not self.mode:
            return

        try:
            key = f"last_position_{self.mode}_{self.current_bank_id}"
            self.cursor.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (key, str(self.current_index))
            )
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"保存当前位置失败: {str(e)}")

    def create_exam(self):
        """创建组合试卷 - 美化版"""
        if not self.question_bank:
            messagebox.showwarning("警告", "请先加载题库")
            return

        # 创建配置窗口 - 美化版
        config_window = tk.Toplevel(self.root)
        config_window.title("试卷配置")
        config_window.geometry("350x250")  # 适当增大窗口高度确保按钮显示
        config_window.resizable(False, False)
        config_window.transient(self.root)  # 设置为主窗口的子窗口
        config_window.grab_set()  # 模态窗口，阻止操作主窗口
        config_window.configure(bg=self.colors["bg"])

        # 标题栏
        header = tk.Frame(config_window, bg=self.colors["primary"], height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        ttk.Label(
            header,
            text="试卷配置",
            font=(self.font_family, 12, "bold"),
            background=self.colors["primary"],
            foreground="white"
        ).pack(pady=8)

        # 统计各题型数量
        total_single = sum(1 for q in self.question_bank if q["type"] == "单选")
        total_multiple = sum(1 for q in self.question_bank if q["type"] == "多选")
        total_judge = sum(1 for q in self.question_bank if q["type"] == "判断")

        # 配置选项
        ttk.Label(
            config_window,
            text="请配置每种题型的数量",
            font=(self.font_family, 12),
            background=self.colors["bg"]
        ).pack(pady=10)

        frame = tk.Frame(config_window, bg=self.colors["bg"])
        frame.pack(pady=5, padx=20, fill=tk.X)

        # 单选题数量 - 使用上次配置的值
        ttk.Label(
            frame,
            text="单选题数量:",
            font=(self.font_family, 10),
            background=self.colors["bg"]
        ).grid(row=0, column=0, padx=5, pady=8, sticky=tk.W)
        single_var = tk.IntVar(value=min(self.exam_config['single'], total_single))
        single_spin = tk.Spinbox(frame, from_=0, to=total_single, textvariable=single_var, width=5,
                                 font=(self.font_family, 10))
        single_spin.grid(row=0, column=1, padx=5, pady=8)
        ttk.Label(
            frame,
            text=f"(最多{total_single}题)",
            font=(self.font_family, 9),
            foreground=self.colors["text_light"],
            background=self.colors["bg"]
        ).grid(row=0, column=2, padx=5, sticky=tk.W)

        # 多选题数量 - 使用上次配置的值
        ttk.Label(
            frame,
            text="多选题数量:",
            font=(self.font_family, 10),
            background=self.colors["bg"]
        ).grid(row=1, column=0, padx=5, pady=8, sticky=tk.W)
        multiple_var = tk.IntVar(value=min(self.exam_config['multiple'], total_multiple))
        multiple_spin = tk.Spinbox(frame, from_=0, to=total_multiple, textvariable=multiple_var, width=5,
                                   font=(self.font_family, 10))
        multiple_spin.grid(row=1, column=1, padx=5, pady=8)
        ttk.Label(
            frame,
            text=f"(最多{total_multiple}题)",
            font=(self.font_family, 9),
            foreground=self.colors["text_light"],
            background=self.colors["bg"]
        ).grid(row=1, column=2, padx=5, sticky=tk.W)

        # 判断题数量 - 使用上次配置的值
        ttk.Label(
            frame,
            text="判断题数量:",
            font=(self.font_family, 10),
            background=self.colors["bg"]
        ).grid(row=2, column=0, padx=5, pady=8, sticky=tk.W)
        judge_var = tk.IntVar(value=min(self.exam_config['judge'], total_judge))
        judge_spin = tk.Spinbox(frame, from_=0, to=total_judge, textvariable=judge_var, width=5,
                                font=(self.font_family, 10))
        judge_spin.grid(row=2, column=1, padx=5, pady=8)
        ttk.Label(
            frame,
            text=f"(最多{total_judge}题)",
            font=(self.font_family, 9),
            foreground=self.colors["text_light"],
            background=self.colors["bg"]
        ).grid(row=2, column=2, padx=5, sticky=tk.W)

        # 按钮框架 - 确保按钮显示
        btn_frame = tk.Frame(config_window, bg=self.colors["bg"])
        btn_frame.pack(pady=15, fill=tk.X, padx=20)  # 增加填充确保显示

        # 确定按钮点击事件
        def confirm():
            single_count = single_var.get()
            multiple_count = multiple_var.get()
            judge_count = judge_var.get()

            if single_count + multiple_count + judge_count == 0:
                messagebox.showwarning("警告", "至少选择一道题")
                return

            # 保存当前配置
            self.exam_config['single'] = single_count
            self.exam_config['multiple'] = multiple_count
            self.exam_config['judge'] = judge_count
            self.save_exam_config()

            # 生成试卷 - 按题型顺序添加题目
            self.current_questions = []

            # 添加单选题
            single_questions = [q for q in self.question_bank if q["type"] == "单选"]
            self.current_questions.extend(random.sample(single_questions, single_count) if single_count > 0 else [])

            # 添加多选题
            multiple_questions = [q for q in self.question_bank if q["type"] == "多选"]
            self.current_questions.extend(
                random.sample(multiple_questions, multiple_count) if multiple_count > 0 else [])

            # 添加判断题
            judge_questions = [q for q in self.question_bank if q["type"] == "判断"]
            self.current_questions.extend(random.sample(judge_questions, judge_count) if judge_count > 0 else [])

            self.mode = "exam"
            self.current_index = 0
            self.user_answers = {}

            # 初始化考试结果
            self.exam_results = {
                "total": len(self.current_questions),
                "correct": 0,
                "wrong": 0,
                "scores": 0,
                "total_scores": sum(float(q["score"]) for q in self.current_questions)
            }

            config_window.destroy()
            self.init_question_interface()
            self.update_question_display()
            self.update_progress_display()

        # 确定按钮
        tk.Button(
            btn_frame,
            text="确定",
            command=confirm,
            width=12,
            bg=self.colors["primary"],
            foreground="white",
            activebackground="#3367d6",
            relief=tk.FLAT
        ).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        # 取消按钮
        tk.Button(
            btn_frame,
            text="取消",
            command=config_window.destroy,
            width=12,
            bg="#f1f3f4",
            foreground=self.colors["text"],
            activebackground=self.colors["hover"],
            relief=tk.FLAT
        ).pack(side=tk.RIGHT, padx=10, fill=tk.X, expand=True)

    def init_question_interface(self):
        """初始化答题界面的固定部分，只执行一次 - 美化版"""
        # 清空当前界面
        for widget in self.root.winfo_children():
            widget.destroy()

        # 顶部标题栏
        header_frame = tk.Frame(self.root, bg=self.colors["primary"], height=50)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        title_label = ttk.Label(
            header_frame,
            text="题刷刷",
            font=(self.font_family, 14, "bold"),
            background=self.colors["primary"],
            foreground="white"
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=10)

        # 创建主容器，分为左侧进度和右侧内容
        main_container = tk.Frame(self.root, bg=self.colors["bg"])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧：答题进度 - 按题型分组显示，带滚动条
        progress_frame = tk.Frame(
            main_container,
            width=180,
            bd=1,
            relief=tk.SOLID,
            bg=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1
        )
        progress_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # 进度区标题
        ttk.Label(
            progress_frame,
            text="答题进度",
            font=(self.font_family, 12, "bold"),
            background=self.colors["card"]
        ).pack(pady=10)

        # 创建滚动区域
        self.progress_canvas = tk.Canvas(progress_frame, bg=self.colors["card"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(progress_frame, orient="vertical", command=self.progress_canvas.yview)
        self.progress_scrollable_frame = tk.Frame(self.progress_canvas, bg=self.colors["card"])

        # 绑定滚动事件
        self.progress_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.progress_canvas.configure(scrollregion=self.progress_canvas.bbox("all"))
        )

        # 创建窗口并关联滚动条
        self.progress_canvas.create_window((0, 0), window=self.progress_scrollable_frame, anchor="nw")
        self.progress_canvas.configure(yscrollcommand=scrollbar.set)

        # 添加鼠标滚轮支持
        self.progress_canvas.bind_all("<MouseWheel>", lambda e: self._on_mouse_wheel(e, self.progress_canvas))

        # 布局滚动区域
        self.progress_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 存储进度区域的框架，用于后续更新
        self.progress_frames = {
            "container": progress_frame,
            "single": None,
            "multiple": None,
            "judge": None,
            "canvas": self.progress_canvas,
            "scrollable": self.progress_scrollable_frame
        }

        # 右侧：题目内容容器
        content_container = tk.Frame(main_container, bg=self.colors["bg"])
        content_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建导航栏
        nav_frame = tk.Frame(content_container, bg=self.colors["card"], relief=tk.SOLID, bd=1, highlightthickness=0)
        nav_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(
            nav_frame,
            text="返回主界面",
            command=self.create_main_interface,
            bg="#f1f3f4",
            activebackground=self.colors["hover"],
            padx=5,
            relief=tk.FLAT,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=10, pady=8)

        # 题目信息区域（用于后续更新）
        self.info_frame = tk.Frame(nav_frame, bg=self.colors["card"])
        self.info_frame.pack(side=tk.RIGHT, padx=10, pady=5)

        # 创建内容滚动区域
        content_scroll_frame = tk.Frame(content_container, bg=self.colors["bg"])
        content_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.content_canvas = tk.Canvas(content_scroll_frame, bg=self.colors["bg"], highlightthickness=0)
        content_scrollbar = ttk.Scrollbar(content_scroll_frame, orient="vertical", command=self.content_canvas.yview)
        self.content_frame = tk.Frame(self.content_canvas, bg=self.colors["bg"])

        self.content_frame.bind(
            "<Configure>",
            lambda e: self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))
        )

        self.content_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        self.content_canvas.configure(yscrollcommand=content_scrollbar.set)

        # 添加鼠标滚轮支持
        self.content_canvas.bind_all("<MouseWheel>", lambda e: self._on_mouse_wheel(e, self.content_canvas))

        self.content_canvas.pack(side="left", fill="both", expand=True)
        content_scrollbar.pack(side="right", fill="y")

        # 解析区域（用于后续更新）
        self.analysis_frame = tk.Frame(content_container, bg=self.colors["bg"])
        self.analysis_label = ttk.Label(
            self.analysis_frame,
            text="",
            font=(self.font_family, 11),
            wraplength=700,
            justify=tk.LEFT,
            foreground=self.colors["primary"],
            background=self.colors["bg"]
        )
        self.analysis_label.pack(anchor=tk.W)

        # 按钮框架
        self.btn_frame = tk.Frame(content_container, bg=self.colors["bg"])
        self.btn_frame.pack(fill=tk.X, padx=10, pady=10)

        # 创建按钮（后续会根据需要更新状态）
        self.prev_btn = tk.Button(
            self.btn_frame,
            text="上一题",
            command=self.prev_question,
            width=15,
            bg="#f1f3f4",
            activebackground=self.colors["hover"],
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.prev_btn.pack(side=tk.LEFT, padx=10)

        self.submit_btn = tk.Button(
            self.btn_frame,
            text="查看解析",
            command=self.submit_answer_and_view_analysis,
            width=15,
            bg=self.colors["primary"],
            foreground="white",
            activebackground="#3367d6",
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.submit_btn.pack(side=tk.LEFT, padx=10)

        self.next_btn = tk.Button(
            self.btn_frame,
            text="下一题",
            command=self.next_question,
            width=15,
            bg="#f1f3f4",
            activebackground=self.colors["hover"],
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.next_btn.pack(side=tk.LEFT, padx=10)

        self.mark_btn = tk.Button(
            self.btn_frame,
            text="标记为错题",
            command=self.mark_as_wrong,
            width=15,
            bg=self.colors["warning"],
            foreground="white",
            activebackground="#f9a825",
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.mark_btn.pack(side=tk.RIGHT, padx=10)

    def _on_mouse_wheel(self, event, canvas):
        """鼠标滚轮事件处理函数"""
        # 确保事件发生在当前canvas上
        if canvas.winfo_containing(event.x_root, event.y_root) == canvas:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def update_progress_display(self):
        """更新进度区域显示，实现连续编号逻辑，并且题型下第一个方框顶格显示"""
        # 清除现有进度框
        for widget in self.progress_frames["scrollable"].winfo_children():
            widget.destroy()

        # 重置索引映射
        self.question_index_map = {}

        # 按题型分组
        single_questions = [q for q in self.current_questions if q["type"] == "单选"]
        multiple_questions = [q for q in self.current_questions if q["type"] == "多选"]
        judge_questions = [q for q in self.current_questions if q["type"] == "判断"]

        # 计算起始编号
        single_start = 1
        multiple_start = single_start + len(single_questions)
        judge_start = multiple_start + len(multiple_questions)

        # 1. 单选题进度
        if single_questions:
            ttk.Label(
                self.progress_frames["scrollable"],
                text="单选题",
                font=(self.font_family, 10, "bold"),
                background=self.colors["card"]
            ).pack(anchor=tk.W, padx=10, pady=5)

            single_frame = tk.Frame(self.progress_frames["scrollable"], bg=self.colors["card"])
            single_frame.pack(fill=tk.X, padx=10, pady=5)
            self.progress_frames["single"] = single_frame

            # 为单选题创建进度框 - 从第一列开始，不留空位
            for i, q in enumerate(single_questions):
                # 找到在当前题目列表中的实际索引
                actual_index = self.current_questions.index(q)
                # 计算显示的编号
                display_number = single_start + i
                # 创建进度框并记录映射关系
                box_id = f"single_{i}"
                self.question_index_map[box_id] = actual_index
                self.create_progress_box(single_frame, display_number, q["id"], box_id, i)

        # 2. 多选题进度
        if multiple_questions:
            ttk.Label(
                self.progress_frames["scrollable"],
                text="多选题",
                font=(self.font_family, 10, "bold"),
                background=self.colors["card"]
            ).pack(anchor=tk.W, padx=10, pady=5)

            multiple_frame = tk.Frame(self.progress_frames["scrollable"], bg=self.colors["card"])
            multiple_frame.pack(fill=tk.X, padx=10, pady=5)
            self.progress_frames["multiple"] = multiple_frame

            # 为多选题创建进度框 - 从第一列开始，不留空位
            for i, q in enumerate(multiple_questions):
                # 找到在当前题目列表中的实际索引
                actual_index = self.current_questions.index(q)
                # 计算显示的编号
                display_number = multiple_start + i
                # 创建进度框并记录映射关系
                box_id = f"multiple_{i}"
                self.question_index_map[box_id] = actual_index
                self.create_progress_box(multiple_frame, display_number, q["id"], box_id, i)

        # 3. 判断题进度
        if judge_questions:
            ttk.Label(
                self.progress_frames["scrollable"],
                text="判断题",
                font=(self.font_family, 10, "bold"),
                background=self.colors["card"]
            ).pack(anchor=tk.W, padx=10, pady=5)

            judge_frame = tk.Frame(self.progress_frames["scrollable"], bg=self.colors["card"])
            judge_frame.pack(fill=tk.X, padx=10, pady=5)
            self.progress_frames["judge"] = judge_frame

            # 为判断题创建进度框 - 从第一列开始，不留空位
            for i, q in enumerate(judge_questions):
                # 找到在当前题目列表中的实际索引
                actual_index = self.current_questions.index(q)
                # 计算显示的编号
                display_number = judge_start + i
                # 创建进度框并记录映射关系
                box_id = f"judge_{i}"
                self.question_index_map[box_id] = actual_index
                self.create_progress_box(judge_frame, display_number, q["id"], box_id, i)

        # 更新滚动区域
        self.progress_frames["canvas"].update_idletasks()
        self.progress_frames["canvas"].configure(scrollregion=self.progress_frames["canvas"].bbox("all"))

    def update_question_display(self):
        """更新题目内容显示，实现连续编号显示，并添加答题状态"""
        # 保存当前位置
        self.save_current_position()

        # ... 原有代码保持不变 ...
        # 清除内容区域现有控件
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # 清除信息区域现有控件
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        # 隐藏解析区域
        self.analysis_frame.pack_forget()

        # 获取当前题目
        question = self.current_questions[self.current_index]

        # 计算当前题目的全局编号
        single_count = sum(1 for q in self.current_questions[:self.current_index + 1] if q["type"] == "单选")
        multiple_count = sum(1 for q in self.current_questions[:self.current_index + 1] if q["type"] == "多选")
        judge_count = sum(1 for q in self.current_questions[:self.current_index + 1] if q["type"] == "判断")

        # 计算当前题目的显示编号
        if question["type"] == "单选":
            display_number = single_count
        elif question["type"] == "多选":
            display_number = sum(1 for q in self.current_questions if q["type"] == "单选") + multiple_count
        else:  # 判断
            display_number = sum(1 for q in self.current_questions if q["type"] in ["单选", "多选"]) + judge_count

        # 添加答题状态 - 未答/已答
        is_answered = question["id"] in self.user_answers and self.user_answers[question["id"]]
        status_text = "已答" if is_answered else "未答"
        status_color = self.colors["success"] if is_answered else self.colors["danger"]

        # 更新题目信息 - 包含答题状态
        status_label = ttk.Label(
            self.info_frame,
            text=status_text,
            font=(self.font_family, 10, "bold"),
            foreground=status_color,
            background=self.colors["card"]
        )
        status_label.pack(side=tk.LEFT, padx=10)

        ttk.Label(
            self.info_frame,
            text=f"题型: {question['type']}",
            font=(self.font_family, 10),
            background=self.colors["card"]
        ).pack(side=tk.LEFT, padx=10)

        ttk.Label(
            self.info_frame,
            text=f"难度: {question['difficulty']}",
            font=(self.font_family, 10),
            background=self.colors["card"]
        ).pack(side=tk.LEFT, padx=10)

        ttk.Label(
            self.info_frame,
            text=f"分数: {question['score']}",
            font=(self.font_family, 10),
            background=self.colors["card"]
        ).pack(side=tk.LEFT, padx=10)

        ttk.Label(
            self.info_frame,
            text=f"第 {display_number}/{len(self.current_questions)} 题",
            font=(self.font_family, 10),
            background=self.colors["card"]
        ).pack(side=tk.LEFT, padx=10)

        # 题目内容
        content_frame = tk.Frame(self.content_frame, bg=self.colors["card"], bd=1, relief=tk.SOLID, padx=15, pady=15)
        content_frame.pack(fill=tk.X, pady=10)

        ttk.Label(
            content_frame,
            text=f"题目: {question['content']}",
            font=(self.font_family, 12),
            wraplength=700,
            justify=tk.LEFT,
            background=self.colors["card"]
        ).pack(anchor=tk.W, pady=10)

        # 选项框架
        options_frame = tk.Frame(content_frame, bg=self.colors["card"])
        options_frame.pack(fill=tk.BOTH, expand=True, anchor=tk.W, pady=10)

        # 存储用户选择的变量
        self.var = tk.StringVar(value="")  # 初始化为空，确保不选中任何选项
        self.check_vars = []

        # 根据题型显示不同的选项
        if question["type"] in ["单选", "判断"]:
            # 单选题或判断题，使用Radiobutton
            for i, option in enumerate(question["options"]):
                # 对于判断题，选项显示为"正确"和"错误"
                if question["type"] == "判断":
                    display_text = option
                    value = option
                else:
                    display_text = f"{chr(65 + i)}. {option}"
                    value = chr(65 + i)

                # 创建单选按钮，并绑定选择事件
                rb = tk.Radiobutton(
                    options_frame,
                    text=display_text,
                    variable=self.var,
                    value=value,
                    font=(self.font_family, 11),
                    anchor=tk.W,
                    bg=self.colors["card"],
                    command=lambda q=question: self.auto_save_answer(q),
                    cursor="hand2"
                )
                rb.pack(fill=tk.X, pady=5, padx=5)

                # 如果用户之前回答过这道题，恢复选择
                if question["id"] in self.user_answers:
                    self.var.set(self.user_answers[question["id"]])
                else:
                    # 确保新题目没有默认选中
                    self.var.set("")
        elif question["type"] == "多选":
            # 多选题，使用Checkbutton
            self.check_vars = []
            for i, option in enumerate(question["options"]):
                var = tk.BooleanVar()
                self.check_vars.append((chr(65 + i), var))
                # 创建复选按钮，并绑定选择事件
                cb = tk.Checkbutton(
                    options_frame,
                    text=f"{chr(65 + i)}. {option}",
                    variable=var,
                    font=(self.font_family, 11),
                    anchor=tk.W,
                    bg=self.colors["card"],
                    command=lambda q=question: self.auto_save_answer(q),
                    cursor="hand2"
                )
                cb.pack(fill=tk.X, pady=5, padx=5)

            # 如果用户之前回答过这道题，恢复选择
            if question["id"] in self.user_answers:
                user_answer = self.user_answers[question["id"]]
                for char, var in self.check_vars:
                    var.set(char in user_answer)

        # 更新按钮状态
        self.prev_btn.config(state=tk.NORMAL if self.current_index > 0 else tk.DISABLED)
        if self.current_index == len(self.current_questions) - 1 and self.mode == "exam":
            self.next_btn.config(text="交卷", command=self.submit_exam)
        else:
            self.next_btn.config(text="下一题", command=self.next_question)

        # 绑定当前题目到按钮命令
        self.submit_btn.config(command=lambda: self.submit_answer_and_view_analysis(question))
        self.mark_btn.config(command=lambda: self.mark_as_wrong(question))

        # 更新进度框高亮状态
        self.highlight_current_progress_box()

    def create_progress_box(self, parent, display_number, question_id, box_id, index):
        """创建答题进度方框，按题型分组显示并支持点击跳转，从第一列开始"""
        # 确定方框颜色
        bg_color = self.colors["success"] if question_id in self.user_answers else self.colors["card"]
        fg_color = "white" if question_id in self.user_answers else self.colors["text"]

        box_frame = tk.Frame(
            parent,
            width=28,
            height=28,
            bd=2,
            relief=tk.SOLID,
            bg=bg_color,
            highlightthickness=0,
            cursor="hand2"
        )

        # 添加点击事件，允许通过点击进度框跳转到对应题目
        # 使用lambda函数确保每次绑定都使用当前的box_id值
        def on_click(event, bid=box_id):
            self.jump_to_question_by_box_id(bid)

        box_frame.bind("<Button-1>", on_click)

        # 添加悬停效果
        box_frame.bind("<Enter>",
                       lambda e: e.widget.configure(relief=tk.RAISED) if e.widget["relief"] != tk.RAISED else None)
        box_frame.bind("<Leave>", lambda e: e.widget.configure(relief=tk.SOLID) if self.question_index_map.get(
            getattr(e.widget, 'box_id', ''), -1) != self.current_index else None)

        # 存储box_id以便后续引用
        box_frame.box_id = box_id
        # 显示全局编号
        box_label = ttk.Label(
            box_frame,
            text=str(display_number),
            font=(self.font_family, 9),
            background=bg_color,
            foreground=fg_color
        )
        box_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 为标签绑定相同的点击事件
        box_label.bind("<Button-1>", lambda e, bid=box_id: self.jump_to_question_by_box_id(bid))

        # 存储方框引用，便于后续更新高亮状态
        self.progress_frames[box_id] = box_frame

        # 按题型内顺序排列，每行显示5个，从第一列开始（index % 5确保从0开始）
        box_frame.grid(row=index // 5, column=index % 5, padx=3, pady=3)
        box_frame.grid_propagate(False)

        return box_frame

    def highlight_current_progress_box(self):
        """高亮显示当前题目的进度框"""
        # 重置所有进度框的边框
        for box_id, frame in self.progress_frames.items():
            if box_id in ["container", "single", "multiple", "judge", "canvas", "scrollable"]:
                continue
            if self.question_index_map.get(box_id, -1) == self.current_index:
                frame.configure(bd=3, relief=tk.RAISED)
            else:
                frame.configure(bd=2, relief=tk.SOLID)

    def jump_to_question_by_box_id(self, box_id):
        """通过进度框ID跳转到对应的题目"""
        # 验证box_id是否有效
        if box_id not in self.question_index_map:
            print(f"无效的box_id: {box_id}")
            return

        target_index = self.question_index_map[box_id]

        # 验证目标索引是否有效
        if target_index < 0 or target_index >= len(self.current_questions):
            print(f"无效的目标索引: {target_index}")
            return

        # 跳转到目标题目
        self.current_index = target_index
        self.update_question_display()

    def jump_to_question(self, index):
        """跳转到指定索引的题目"""
        self.current_index = index
        self.update_question_display()

    def get_user_answer(self, question_type):
        """获取用户答案"""
        if question_type in ["单选", "判断"]:
            return self.var.get()
        elif question_type == "多选":
            return "".join([char for char, var in self.check_vars if var.get()])
        return ""

    def auto_save_answer(self, question):
        """自动保存用户答案到数据库"""
        user_answer = self.get_user_answer(question["type"])
        if user_answer:  # 只有当有答案时才保存
            self.user_answers[question["id"]] = user_answer

            try:
                # 插入或更新答题记录
                self.cursor.execute('''
                INSERT OR REPLACE INTO progress 
                (bank_id, mode, question_id, user_answer, answered_at)
                VALUES (?, ?, ?, ?, ?)
                ''', (self.current_bank_id, self.mode, question["id"], user_answer, datetime.now()))
                self.conn.commit()

                # 只更新对应进度框的颜色，不刷新整个进度区
                for box_id, idx in self.question_index_map.items():
                    if idx == self.current_index and box_id in self.progress_frames:
                        frame = self.progress_frames[box_id]
                        frame.configure(bg=self.colors["success"])
                        # 更新标签背景色和前景色
                        for widget in frame.winfo_children():
                            if isinstance(widget, ttk.Label):
                                widget.configure(background=self.colors["success"], foreground="white")

                # 更新答题状态
                for widget in self.info_frame.winfo_children():
                    if isinstance(widget, ttk.Label) and widget["text"] in ["未答", "已答"]:
                        widget["text"] = "已答"
                        widget["foreground"] = self.colors["success"]

            except sqlite3.Error as e:
                self.conn.rollback()
                messagebox.showerror("数据库错误", f"保存答案失败: {str(e)}")

    def submit_answer_and_view_analysis(self, question):
        """查看解析"""
        user_answer = self.get_user_answer(question["type"])

        if not user_answer:
            messagebox.showwarning("警告", "请选择答案后再提交")
            return

        # 保存用户答案
        self.user_answers[question["id"]] = user_answer

        try:
            # 插入或更新答题记录
            self.cursor.execute('''
            INSERT OR REPLACE INTO progress 
            (bank_id, mode, question_id, user_answer, answered_at)
            VALUES (?, ?, ?, ?, ?)
            ''', (self.current_bank_id, self.mode, question["id"], user_answer, datetime.now()))
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            messagebox.showerror("数据库错误", f"查看解析失败: {str(e)}")

        # 显示解析区域
        self.analysis_frame.pack(fill=tk.BOTH, expand=True, anchor=tk.W, pady=10)

        # 显示正确答案和解析
        self.analysis_label.config(text=f"正确答案: {question['answer']}\n\n解析: {question['analysis']}")

        # 判断答案是否正确
        is_correct = user_answer == question["answer"]

        # 如果答案错误，自动添加到错题集
        if not is_correct:
            self.add_to_wrong_questions(question, user_answer)

        # 高亮显示正确和错误的选项
        for widget in self.content_frame.winfo_children():
            if isinstance(widget, tk.Frame):  # 选项框架
                for child in widget.winfo_children():
                    if isinstance(child, tk.Frame):  # 内容框架
                        for option_widget in child.winfo_children():
                            if isinstance(option_widget, (tk.Radiobutton, tk.Checkbutton)):
                                # 禁用选项，防止再次修改
                                option_widget.config(state=tk.DISABLED)

                                # 获取选项值
                                if question["type"] in ["单选", "判断"]:
                                    value = option_widget.cget("value")
                                else:  # 多选
                                    text = option_widget.cget("text")
                                    value = text[0]  # 取选项字母A/B/C/D

                                # 正确答案高亮显示为绿色
                                if value in question["answer"]:
                                    option_widget.config(foreground=self.colors["success"],
                                                         font=(self.font_family, 11, "bold"))
                                # 用户选择的错误答案显示为红色
                                elif value in user_answer and value not in question["answer"]:
                                    option_widget.config(foreground=self.colors["danger"],
                                                         font=(self.font_family, 11, "bold"))

        # 更新进度框颜色
        for box_id, idx in self.question_index_map.items():
            if idx == self.current_index and box_id in self.progress_frames:
                frame = self.progress_frames[box_id]
                frame.configure(bg=self.colors["success"])
                # 更新标签背景色和前景色
                for widget in frame.winfo_children():
                    if isinstance(widget, ttk.Label):
                        widget.configure(background=self.colors["success"], foreground="white")

        # 更新答题状态
        for widget in self.info_frame.winfo_children():
            if isinstance(widget, ttk.Label) and widget["text"] in ["未答", "已答"]:
                widget["text"] = "已答"
                widget["foreground"] = self.colors["success"]

    def prev_question(self):
        """上一题 - 按照进度框显示顺序"""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_question_display()
        else:
            messagebox.showinfo("提示", "已经是第一题了")

    def next_question(self):
        """下一题 - 按照进度框显示顺序"""
        if self.current_index < len(self.current_questions) - 1:
            self.current_index += 1
            self.update_question_display()
        else:
            if self.mode == "exam":
                self.submit_exam()
            else:
                messagebox.showinfo("完成", "恭喜您完成所有题目练习！")
                self.create_main_interface()

    def submit_exam(self):
        """提交试卷"""
        # 检查是否有未回答的题目
        unanswerd = []
        for i, question in enumerate(self.current_questions):
            if question["id"] not in self.user_answers:
                # 计算未答题目编号
                single_count = sum(1 for q in self.current_questions[:i + 1] if q["type"] == "单选")
                multiple_count = sum(1 for q in self.current_questions[:i + 1] if q["type"] == "多选")
                judge_count = sum(1 for q in self.current_questions[:i + 1] if q["type"] == "判断")

                if question["type"] == "单选":
                    display_number = single_count
                elif question["type"] == "多选":
                    display_number = sum(1 for q in self.current_questions if q["type"] == "单选") + multiple_count
                else:  # 判断
                    display_number = sum(
                        1 for q in self.current_questions if q["type"] in ["单选", "多选"]) + judge_count

                unanswerd.append(display_number)

        if unanswerd:
            if not messagebox.askyesno("提示",
                                       f"您有 {len(unanswerd)} 道题未回答，确定要交卷吗？\n未回答题目: {', '.join(map(str, unanswerd))}"):
                return

        # 计算成绩
        self.calculate_exam_result()
        self.show_exam_result()

    def calculate_exam_result(self):
        """计算考试结果"""
        correct_count = 0
        total_score = 0

        for question in self.current_questions:
            if question["id"] in self.user_answers:
                user_answer = self.user_answers[question["id"]]
                is_correct = user_answer == question["answer"]

                if is_correct:
                    correct_count += 1
                    total_score += float(question["score"])
                else:
                    # 添加到错题集
                    self.add_to_wrong_questions(question, user_answer)
            else:
                # 未答题也视为错误
                self.add_to_wrong_questions(question, "")
                is_correct = False

            # 计算题目编号
            single_count = sum(
                1 for q in self.current_questions[:self.current_questions.index(question) + 1] if q["type"] == "单选")
            multiple_count = sum(
                1 for q in self.current_questions[:self.current_questions.index(question) + 1] if q["type"] == "多选")
            judge_count = sum(
                1 for q in self.current_questions[:self.current_questions.index(question) + 1] if q["type"] == "判断")

            if question["type"] == "单选":
                display_number = single_count
            elif question["type"] == "多选":
                display_number = sum(1 for q in self.current_questions if q["type"] == "单选") + multiple_count
            else:  # 判断
                display_number = sum(1 for q in self.current_questions if q["type"] in ["单选", "多选"]) + judge_count

            # 记录每道题的答题情况
            self.exam_results[question["id"]] = {
                "content": question["content"],
                "type": question["type"],
                "user_answer": self.user_answers.get(question["id"], "未回答"),
                "correct_answer": question["answer"],
                "is_correct": is_correct,
                "score": float(question["score"]) if is_correct else 0,
                "total_score": float(question["score"]),
                "number": display_number
            }

        self.exam_results["correct"] = correct_count
        self.exam_results["wrong"] = len(self.current_questions) - correct_count
        self.exam_results["scores"] = total_score
        self.exam_results["total"] = len(self.current_questions)
        self.exam_results["total_scores"] = sum(float(q["score"]) for q in self.current_questions)

    def show_exam_result(self):
        """显示考试结果，包括答题卡 - 美化版"""
        # 清空当前界面
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.configure(bg=self.colors["bg"])

        # 顶部标题栏
        header_frame = tk.Frame(self.root, bg=self.colors["primary"], height=50)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        title_label = ttk.Label(
            header_frame,
            text="考试结果",
            font=(self.font_family, 14, "bold"),
            background=self.colors["primary"],
            foreground="white"
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=10)

        # 结果统计卡片
        stats_card = tk.Frame(
            self.root,
            bg=self.colors["card"],
            bd=1,
            relief=tk.SOLID,
            padx=20,
            pady=15
        )
        stats_card.pack(fill=tk.X, padx=50, pady=20)

        ttk.Label(
            stats_card,
            text=f"总题数: {self.exam_results['total']}",
            font=(self.font_family, 12),
            background=self.colors["card"]
        ).grid(row=0, column=0, padx=30, pady=10)

        ttk.Label(
            stats_card,
            text=f"做对: {self.exam_results['correct']}",
            font=(self.font_family, 12),
            foreground=self.colors["success"],
            background=self.colors["card"]
        ).grid(row=0, column=1, padx=30, pady=10)

        ttk.Label(
            stats_card,
            text=f"做错: {self.exam_results['wrong']}",
            font=(self.font_family, 12),
            foreground=self.colors["danger"],
            background=self.colors["card"]
        ).grid(row=0, column=2, padx=30, pady=10)

        ttk.Label(
            stats_card,
            text=f"得分: {self.exam_results['scores']}/{self.exam_results['total_scores']}",
            font=(self.font_family, 12),
            background=self.colors["card"]
        ).grid(row=0, column=3, padx=30, pady=10)

        # 创建一个笔记本组件来按题型显示结果
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 按题型分类
        single_frame = tk.Frame(notebook, bg=self.colors["bg"])
        multiple_frame = tk.Frame(notebook, bg=self.colors["bg"])
        judge_frame = tk.Frame(notebook, bg=self.colors["bg"])

        notebook.add(single_frame, text="单选题")
        notebook.add(multiple_frame, text="多选题")
        notebook.add(judge_frame, text="判断题")

        # 为每个题型创建滚动区域
        single_canvas = tk.Canvas(single_frame, bg=self.colors["bg"])
        single_scrollbar = ttk.Scrollbar(single_frame, orient="vertical", command=single_canvas.yview)
        single_scrollable_frame = tk.Frame(single_canvas, bg=self.colors["bg"])

        single_scrollable_frame.bind(
            "<Configure>",
            lambda e: single_canvas.configure(scrollregion=single_canvas.bbox("all"))
        )

        single_canvas.create_window((0, 0), window=single_scrollable_frame, anchor="nw")
        single_canvas.configure(yscrollcommand=single_scrollbar.set)

        # 添加鼠标滚轮支持
        single_canvas.bind_all("<MouseWheel>", lambda e: self._on_mouse_wheel(e, single_canvas))

        single_canvas.pack(side="left", fill="both", expand=True)
        single_scrollbar.pack(side="right", fill="y")

        # 多选题滚动区域
        multiple_canvas = tk.Canvas(multiple_frame, bg=self.colors["bg"])
        multiple_scrollbar = ttk.Scrollbar(multiple_frame, orient="vertical", command=multiple_canvas.yview)
        multiple_scrollable_frame = tk.Frame(multiple_canvas, bg=self.colors["bg"])

        multiple_scrollable_frame.bind(
            "<Configure>",
            lambda e: multiple_canvas.configure(scrollregion=multiple_canvas.bbox("all"))
        )

        multiple_canvas.create_window((0, 0), window=multiple_scrollable_frame, anchor="nw")
        multiple_canvas.configure(yscrollcommand=multiple_scrollbar.set)

        # 添加鼠标滚轮支持
        multiple_canvas.bind_all("<MouseWheel>", lambda e: self._on_mouse_wheel(e, multiple_canvas))

        multiple_canvas.pack(side="left", fill="both", expand=True)
        multiple_scrollbar.pack(side="right", fill="y")

        # 判断题滚动区域
        judge_canvas = tk.Canvas(judge_frame, bg=self.colors["bg"])
        judge_scrollbar = ttk.Scrollbar(judge_frame, orient="vertical", command=judge_canvas.yview)
        judge_scrollable_frame = tk.Frame(judge_canvas, bg=self.colors["bg"])

        judge_scrollable_frame.bind(
            "<Configure>",
            lambda e: judge_canvas.configure(scrollregion=judge_canvas.bbox("all"))
        )

        judge_canvas.create_window((0, 0), window=judge_scrollable_frame, anchor="nw")
        judge_canvas.configure(yscrollcommand=judge_scrollbar.set)

        # 添加鼠标滚轮支持
        judge_canvas.bind_all("<MouseWheel>", lambda e: self._on_mouse_wheel(e, judge_canvas))

        judge_canvas.pack(side="left", fill="both", expand=True)
        judge_scrollbar.pack(side="right", fill="y")

        # 填充各题型结果
        single_count = 0
        multiple_count = 0
        judge_count = 0

        for question in self.current_questions:
            q_id = question["id"]
            result = self.exam_results.get(q_id, {})
            frame_bg = "#e8f5e9" if result.get("is_correct", False) else "#ffebee"

            if question["type"] == "单选":
                single_count += 1
                self.create_question_result_frame(
                    single_scrollable_frame, question, result, single_count, frame_bg
                )
            elif question["type"] == "多选":
                multiple_count += 1
                self.create_question_result_frame(
                    multiple_scrollable_frame, question, result, multiple_count, frame_bg
                )
            elif question["type"] == "判断":
                judge_count += 1
                self.create_question_result_frame(
                    judge_scrollable_frame, question, result, judge_count, frame_bg
                )

        # 显示答题卡标题
        ttk.Label(
            self.root,
            text="答题卡",
            font=(self.font_family, 14, "bold"),
            background=self.colors["bg"]
        ).pack(pady=10)

        # 答题卡卡片
        answer_sheet_card = tk.Frame(
            self.root,
            bg=self.colors["card"],
            bd=1,
            relief=tk.SOLID,
            padx=20,
            pady=15
        )
        answer_sheet_card.pack(fill=tk.X, padx=50, pady=10)

        # 单选题答题卡
        single_sheet_frame = tk.Frame(answer_sheet_card, bg=self.colors["card"])
        single_sheet_frame.pack(fill=tk.X, pady=10)

        ttk.Label(
            single_sheet_frame,
            text="单选题:",
            font=(self.font_family, 10, "bold"),
            background=self.colors["card"]
        ).pack(side=tk.LEFT, padx=10)

        single_questions = [q for q in self.current_questions if q["type"] == "单选"]
        for q in single_questions:
            result = self.exam_results.get(q["id"], {})
            color = self.colors["success"] if result.get("is_correct", False) else self.colors["danger"]

            box_frame = tk.Frame(
                single_sheet_frame,
                width=25,
                height=25,
                bd=1,
                relief=tk.SOLID,
                bg=color,
                cursor="hand2"
            )
            box_frame.pack(side=tk.LEFT, padx=2, pady=2)
            box_frame.grid_propagate(False)

            ttk.Label(
                box_frame,
                text=str(result.get("number", "")),
                font=(self.font_family, 9),
                background=color,
                foreground="white"
            ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 多选题答题卡
        multiple_sheet_frame = tk.Frame(answer_sheet_card, bg=self.colors["card"])
        multiple_sheet_frame.pack(fill=tk.X, pady=10)

        ttk.Label(
            multiple_sheet_frame,
            text="多选题:",
            font=(self.font_family, 10, "bold"),
            background=self.colors["card"]
        ).pack(side=tk.LEFT, padx=10)

        multiple_questions = [q for q in self.current_questions if q["type"] == "多选"]
        for q in multiple_questions:
            result = self.exam_results.get(q["id"], {})
            color = self.colors["success"] if result.get("is_correct", False) else self.colors["danger"]

            box_frame = tk.Frame(
                multiple_sheet_frame,
                width=25,
                height=25,
                bd=1,
                relief=tk.SOLID,
                bg=color,
                cursor="hand2"
            )
            box_frame.pack(side=tk.LEFT, padx=2, pady=2)
            box_frame.grid_propagate(False)

            ttk.Label(
                box_frame,
                text=str(result.get("number", "")),
                font=(self.font_family, 9),
                background=color,
                foreground="white"
            ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 判断题答题卡
        judge_sheet_frame = tk.Frame(answer_sheet_card, bg=self.colors["card"])
        judge_sheet_frame.pack(fill=tk.X, pady=10)

        ttk.Label(
            judge_sheet_frame,
            text="判断题:",
            font=(self.font_family, 10, "bold"),
            background=self.colors["card"]
        ).pack(side=tk.LEFT, padx=10)

        judge_questions = [q for q in self.current_questions if q["type"] == "判断"]
        for q in judge_questions:
            result = self.exam_results.get(q["id"], {})
            color = self.colors["success"] if result.get("is_correct", False) else self.colors["danger"]

            box_frame = tk.Frame(
                judge_sheet_frame,
                width=25,
                height=25,
                bd=1,
                relief=tk.SOLID,
                bg=color,
                cursor="hand2"
            )
            box_frame.pack(side=tk.LEFT, padx=2, pady=2)
            box_frame.grid_propagate(False)

            ttk.Label(
                box_frame,
                text=str(result.get("number", "")),
                font=(self.font_family, 9),
                background=color,
                foreground="white"
            ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 底部按钮
        btn_frame = tk.Frame(self.root, bg=self.colors["bg"])
        btn_frame.pack(fill=tk.X, padx=20, pady=20)

        tk.Button(
            btn_frame,
            text="返回主界面",
            command=self.create_main_interface,
            width=15,
            bg="#f1f3f4",
            activebackground=self.colors["hover"],
            relief=tk.FLAT,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(
            btn_frame,
            text="重新考试",
            command=lambda: self.create_exam(),
            width=15,
            bg=self.colors["primary"],
            foreground="white",
            activebackground="#3367d6",
            relief=tk.FLAT,
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=10)

    def create_question_result_frame(self, parent, question, result, index, bg_color):
        """创建题目结果展示框架 - 美化版"""
        frame = tk.Frame(
            parent,
            bg=bg_color,
            bd=1,
            relief=tk.SOLID,
            padx=15,
            pady=15,
            highlightbackground="#bdbdbd",
            highlightthickness=1
        )
        frame.pack(fill=tk.X, pady=10, padx=10)

        # 题目信息
        info_frame = tk.Frame(frame, bg=bg_color)
        info_frame.pack(fill=tk.X, anchor=tk.W)

        ttk.Label(
            info_frame,
            text=f"第 {result.get('number', index)} 题",
            font=(self.font_family, 10, "bold"),
            background=bg_color
        ).pack(side=tk.LEFT, padx=10)

        ttk.Label(
            info_frame,
            text=f"题型: {question['type']}",
            font=(self.font_family, 10),
            background=bg_color
        ).pack(side=tk.LEFT, padx=10)

        ttk.Label(
            info_frame,
            text=f"难度: {question['difficulty']}",
            font=(self.font_family, 10),
            background=bg_color
        ).pack(side=tk.LEFT, padx=10)

        # 题目内容
        ttk.Label(
            frame,
            text=f"题目: {question['content']}",
            font=(self.font_family, 11),
            wraplength=700,
            justify=tk.LEFT,
            background=bg_color
        ).pack(anchor=tk.W, pady=5)

        # 选项
        options_frame = tk.Frame(frame, bg=bg_color)
        options_frame.pack(fill=tk.X, anchor=tk.W, pady=5)

        for j, option in enumerate(question["options"]):
            if question["type"] == "判断":
                display_text = option
                value = option
            else:
                display_text = f"{chr(65 + j)}. {option}"
                value = chr(65 + j)

            # 标记正确答案和用户选择
            fg_color = "black"
            font_weight = "normal"

            if value in question["answer"]:
                fg_color = self.colors["success"]
                font_weight = "bold"
            elif "user_answer" in result and value in result["user_answer"] and value not in question["answer"]:
                fg_color = self.colors["danger"]
                font_weight = "bold"

            ttk.Label(
                options_frame,
                text=display_text,
                font=(self.font_family, 10, font_weight),
                foreground=fg_color,
                wraplength=700,
                justify=tk.LEFT,
                background=bg_color
            ).pack(anchor=tk.W, pady=2)

        # 答案和解析
        ttk.Label(
            frame,
            text=f"你的答案: {result.get('user_answer', '未回答')}",
            font=(self.font_family, 10),
            justify=tk.LEFT,
            background=bg_color
        ).pack(anchor=tk.W, pady=2)

        ttk.Label(
            frame,
            text=f"正确答案: {question['answer']}",
            font=(self.font_family, 10, "bold"),
            foreground=self.colors["success"],
            justify=tk.LEFT,
            background=bg_color
        ).pack(anchor=tk.W, pady=2)

        ttk.Label(
            frame,
            text=f"解析: {question['analysis']}",
            font=(self.font_family, 10),
            wraplength=700,
            justify=tk.LEFT,
            background=bg_color
        ).pack(anchor=tk.W, pady=2)

        ttk.Label(
            frame,
            text=f"得分: {result.get('score', 0)}/{result.get('total_score', 0)}",
            font=(self.font_family, 10),
            justify=tk.LEFT,
            background=bg_color
        ).pack(anchor=tk.W, pady=2)

    def mark_as_wrong(self, question):
        """标记为错题"""
        try:
            self.cursor.execute(
                "SELECT id FROM wrong_questions WHERE bank_id = ? AND question_id = ?",
                (self.current_bank_id, question["id"])
            )

            if self.cursor.fetchone():
                messagebox.showinfo("提示", "这道题已经在错题集中了")
                return

            # 添加到错题集
            self.cursor.execute('''
            INSERT INTO wrong_questions (bank_id, question_id, user_answer, added_at)
            VALUES (?, ?, ?, ?)
            ''', (self.current_bank_id, question["id"],
                  self.user_answers.get(question["id"], ""), datetime.now()))
            self.conn.commit()

            # 更新内存中的错题集
            self.load_wrong_questions()

            messagebox.showinfo("成功", "已添加到错题集")
        except sqlite3.Error as e:
            self.conn.rollback()
            messagebox.showerror("数据库错误", f"标记错题失败: {str(e)}")

    def add_to_wrong_questions(self, question, user_answer):
        """将错题添加到错题集"""
        try:
            # 检查是否已经在错题集中
            self.cursor.execute(
                "SELECT id FROM wrong_questions WHERE bank_id = ? AND question_id = ?",
                (self.current_bank_id, question["id"])
            )

            if self.cursor.fetchone():
                return

            # 添加到错题集
            self.cursor.execute('''
            INSERT INTO wrong_questions (bank_id, question_id, user_answer, added_at)
            VALUES (?, ?, ?, ?)
            ''', (self.current_bank_id, question["id"], user_answer, datetime.now()))
            self.conn.commit()

            # 更新内存中的错题集
            self.load_wrong_questions()
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"添加错题失败: {str(e)}")

    def load_wrong_questions(self):
        """从数据库加载错题集"""
        self.wrong_questions = []
        if not self.current_bank_id:
            return

        try:
            self.cursor.execute('''
            SELECT q.id, q.content, q.type, q.is_subquestion, q.options, q.difficulty, 
                   q.analysis, q.answer, q.score, w.user_answer
            FROM wrong_questions w
            JOIN questions q ON w.question_id = q.id
            WHERE w.bank_id = ?
            ORDER BY w.added_at DESC
            ''', (self.current_bank_id,))

            for row in self.cursor.fetchall():
                question = {
                    "id": row[0],
                    "content": row[1],
                    "type": row[2],
                    "is_subquestion": row[3],
                    "options": row[4].split('|') if row[4] else [],
                    "difficulty": row[5],
                    "analysis": row[6],
                    "answer": row[7],
                    "score": row[8],
                    "user_answer": row[9]
                }

                # 处理判断题选项
                if question["type"] == "判断" and not question["options"]:
                    question["options"] = ["正确", "错误"]

                self.wrong_questions.append(question)
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"加载错题集失败: {str(e)}")
            self.wrong_questions = []

    def view_wrong_questions(self):
        """查看错题集 - 美化版"""
        if not self.current_bank_id:
            messagebox.showwarning("警告", "请先加载一个题库")
            return

        # 加载最新的错题集
        self.load_wrong_questions()

        if not self.wrong_questions:
            messagebox.showinfo("提示", "错题集为空")
            return

        # 清空当前界面
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.configure(bg=self.colors["bg"])

        # 顶部标题栏
        header_frame = tk.Frame(self.root, bg=self.colors["primary"], height=50)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        title_label = ttk.Label(
            header_frame,
            text="错题集",
            font=(self.font_family, 14, "bold"),
            background=self.colors["primary"],
            foreground="white"
        ).pack(side=tk.LEFT, padx=20, pady=10)

        # 错题集按钮放到标题区下方
        btn_frame = tk.Frame(self.root, bg=self.colors["bg"])
        btn_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Button(
            btn_frame,
            text="返回主界面",
            command=self.create_main_interface,
            width=15,
            bg="#f1f3f4",
            activebackground=self.colors["hover"],
            relief=tk.FLAT,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(
            btn_frame,
            text="练习错题",
            command=lambda: self.practice_wrong_questions(),
            width=15,
            bg=self.colors["primary"],
            foreground="white",
            activebackground="#3367d6",
            relief=tk.FLAT,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=10)

        # 统计信息卡片
        stats_card = tk.Frame(
            self.root,
            bg=self.colors["card"],
            bd=1,
            relief=tk.SOLID,
            padx=20,
            pady=15
        )
        stats_card.pack(fill=tk.X, padx=50, pady=10)

        ttk.Label(
            stats_card,
            text=f"共有 {len(self.wrong_questions)} 道错题",
            font=(self.font_family, 12),
            background=self.colors["card"]
        ).pack()

        # 创建滚动区域
        canvas = tk.Canvas(self.root, bg=self.colors["bg"])
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors["bg"])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 添加鼠标滚轮支持
        canvas.bind_all("<MouseWheel>", lambda e: self._on_mouse_wheel(e, canvas))

        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")

        # 显示错题
        for i, question in enumerate(self.wrong_questions):
            frame = tk.Frame(
                scrollable_frame,
                bd=1,
                relief=tk.SOLID,
                padx=15,
                pady=15,
                bg="#fff3e0",
                highlightbackground="#bdbdbd",
                highlightthickness=1
            )
            frame.pack(fill=tk.X, pady=10, padx=10)

            # 题目信息
            info_frame = tk.Frame(frame, bg="#fff3e0")
            info_frame.pack(fill=tk.X, anchor=tk.W)

            ttk.Label(
                info_frame,
                text=f"第 {i + 1} 题",
                font=(self.font_family, 10, "bold"),
                background="#fff3e0"
            ).pack(side=tk.LEFT, padx=10)

            ttk.Label(
                info_frame,
                text=f"题型: {question['type']}",
                font=(self.font_family, 10),
                background="#fff3e0"
            ).pack(side=tk.LEFT, padx=10)

            ttk.Label(
                info_frame,
                text=f"难度: {question['difficulty']}",
                font=(self.font_family, 10),
                background="#fff3e0"
            ).pack(side=tk.LEFT, padx=10)

            # 题目内容
            ttk.Label(
                frame,
                text=f"题目: {question['content']}",
                font=(self.font_family, 11),
                wraplength=700,
                justify=tk.LEFT,
                background="#fff3e0"
            ).pack(anchor=tk.W, pady=5)

            # 选项
            options_frame = tk.Frame(frame, bg="#fff3e0")
            options_frame.pack(fill=tk.X, anchor=tk.W, pady=5)

            for j, option in enumerate(question["options"]):
                if question["type"] == "判断":
                    display_text = option
                    value = option
                else:
                    display_text = f"{chr(65 + j)}. {option}"
                    value = chr(65 + j)

                # 标记正确答案和用户选择
                fg_color = "black"
                font_weight = "normal"

                if value in question["answer"]:
                    fg_color = self.colors["success"]
                    font_weight = "bold"
                elif "user_answer" in question and value in question["user_answer"] and value not in question["answer"]:
                    fg_color = self.colors["danger"]
                    font_weight = "bold"

                ttk.Label(
                    options_frame,
                    text=display_text,
                    font=(self.font_family, 10, font_weight),
                    foreground=fg_color,
                    wraplength=700,
                    justify=tk.LEFT,
                    background="#fff3e0"
                ).pack(anchor=tk.W, pady=2)

            # 答案和解析
            if "user_answer" in question:
                ttk.Label(
                    frame,
                    text=f"你的答案: {question['user_answer']}",
                    font=(self.font_family, 10),
                    justify=tk.LEFT,
                    background="#fff3e0"
                ).pack(anchor=tk.W, pady=2)

            ttk.Label(
                frame,
                text=f"正确答案: {question['answer']}",
                font=(self.font_family, 10, "bold"),
                foreground=self.colors["success"],
                justify=tk.LEFT,
                background="#fff3e0"
            ).pack(anchor=tk.W, pady=2)

            ttk.Label(
                frame,
                text=f"解析: {question['analysis']}",
                font=(self.font_family, 10),
                wraplength=700,
                justify=tk.LEFT,
                background="#fff3e0"
            ).pack(anchor=tk.W, pady=2)

            # 移除按钮
            tk.Button(
                frame,
                text="从错题集移除",
                command=lambda q=question: self.remove_from_wrong(q),
                bg=self.colors["danger"],
                foreground="white",
                width=15,
                activebackground="#d32f2f",
                relief=tk.FLAT,
                cursor="hand2"
            ).pack(anchor=tk.E, pady=5)

    def remove_from_wrong(self, question):
        """从错题集移除"""
        try:
            self.cursor.execute(
                "DELETE FROM wrong_questions WHERE bank_id = ? AND question_id = ?",
                (self.current_bank_id, question["id"])
            )
            self.conn.commit()

            # 更新内存中的错题集
            self.load_wrong_questions()

            # 刷新界面
            self.view_wrong_questions()
        except sqlite3.Error as e:
            self.conn.rollback()
            messagebox.showerror("数据库错误", f"移除错题失败: {str(e)}")

    def practice_wrong_questions(self):
        """练习错题"""
        if not self.wrong_questions:
            messagebox.showinfo("提示", "错题集为空")
            return

        self.mode = "wrong"
        self.current_questions = self.wrong_questions.copy()
        self.current_index = 0
        self.user_answers = {}

        # 从数据库中加载用户答案
        try:
            self.cursor.execute(
                "SELECT question_id, user_answer FROM progress "
                "WHERE bank_id = ? AND mode = ?",
                (self.current_bank_id, "wrong")
            )

            for row in self.cursor.fetchall():
                self.user_answers[row[0]] = row[1]
        except sqlite3.Error as e:
            messagebox.showerror("数据库错误", f"加载答题进度失败: {str(e)}")
            self.user_answers = {}

        # 显示第一题
        self.init_question_interface()
        self.update_question_display()
        self.update_progress_display()


if __name__ == "__main__":
    root = tk.Tk()
    app = ExamSoftware(root)
    root.mainloop()
