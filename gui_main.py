"""
天地图智能分析系统 - Tkinter 稳定版
✨ 优势：Python 标准库 | 零安装风险 | 100% 兼容所有 Python 3.x
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import sys
import os
import webbrowser
from datetime import datetime

class QueueWriter:
    """将print重定向到队列"""
    def __init__(self, log_queue): self.queue = log_queue
    def write(self, msg): 
        if msg.strip(): self.queue.put(msg)
    def flush(self): pass

def run_analysis(place_name, log_queue):
    """后台执行分析流程"""
    old_stdout = sys.stdout
    sys.stdout = QueueWriter(log_queue)
    
    try:
        # 动态导入（避免启动时依赖）
        from geocoder import get_location_bounds
        from image_fetcher import fetch_tiles
        from image_merger import merge_tiles
        from data_analyzer import analyze_metadata
        from visualization import generate_visualizations
        import config
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🌍 开始分析: {place_name}")
        
        # 地理编码
        bounds, msg = get_location_bounds(place_name)
        
        
        if not bounds:
            print(f"❌ {msg}")
            return False, None
        
        # 下载瓦片
        metadata_df = fetch_tiles(bounds)
        if metadata_df.empty:
            print("❌ 瓦片下载失败")
            return False, None
        
        # 拼接地图
        merge_tiles(metadata_df)
        
        # 分析+可视化
        analysis_result = analyze_metadata(metadata_df)
        generate_visualizations(analysis_result)
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✅ 分析完成！")
        return True, config.ANALYSIS_REPORT
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None
    finally:
        sys.stdout = old_stdout

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("🌍 天地图智能分析系统 | 数据分析项目")
        self.root.geometry("700x500")
        self.root.minsize(600, 400)
        
        # 输入框
        frame_top = tk.Frame(root, padx=10, pady=10)
        frame_top.pack(fill=tk.X)
        
        tk.Label(frame_top, text="📍 输入查询地点（如：北京中关村）:", 
                font=("Microsoft YaHei", 10)).pack(anchor=tk.W)
        
        self.entry = tk.Entry(frame_top, font=("Microsoft YaHei", 10), width=50)
        self.entry.insert(0, "北京中关村")
        self.entry.pack(side=tk.LEFT, padx=(0, 5), pady=5)
        self.entry.bind("<Return>", lambda e: self.start_analysis())
        
        self.btn_run = tk.Button(frame_top, text="🚀 开始分析", 
                               command=self.start_analysis, width=12, bg="#4CAF50", fg="white")
        self.btn_run.pack(side=tk.LEFT, pady=5)
        
        # 日志框
        tk.Label(root, text="📝 运行日志:", font=("Microsoft YaHei", 9), 
                padx=10, anchor=tk.W).pack(anchor=tk.W)
        
        self.log_text = scrolledtext.ScrolledText(
            root, 
            wrap=tk.WORD, 
            font=("Consolas", 9),
            bg="#f5f5f5",
            height=20
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 底部按钮
        frame_bottom = tk.Frame(root, padx=10, pady=5)
        frame_bottom.pack(fill=tk.X)
        
        self.btn_open = tk.Button(frame_bottom, text="📁 打开报告", 
                                command=self.open_report, state=tk.DISABLED, width=15)
        self.btn_open.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(frame_bottom, text="❓ 帮助", 
                command=self.show_help, width=10).pack(side=tk.LEFT)
        tk.Button(frame_bottom, text="🚪 退出", 
                command=root.quit, width=10).pack(side=tk.RIGHT)
        
        self.log_queue = queue.Queue()
        self.report_path = None
        self.after_id = None
        self._update_log()
    
    def log(self, msg):
        """安全写入日志（主线程）"""
        self.log_text.insert(tk.END, msg)
        self.log_text.see(tk.END)
    
    def _update_log(self):
        """定期检查队列更新日志"""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log(msg)
        except queue.Empty:
            pass
        self.after_id = self.root.after(100, self._update_log)
    
    def start_analysis(self):
        place = self.entry.get().strip()
        if not place:
            messagebox.showwarning("提示", "请输入查询地点！")
            return
        
        # 禁用按钮
        self.btn_run.config(state=tk.DISABLED, text="⏳ 处理中...")
        self.btn_open.config(state=tk.DISABLED)
        self.log(f"\n[{datetime.now().strftime('%H:%M:%S')}] 💡 准备分析: {place}\n")
        
        # 启动后台线程
        def thread_target():
            success, report = run_analysis(place, self.log_queue)
            self.root.after(0, lambda: self.analysis_done(success, report))
        
        threading.Thread(target=thread_target, daemon=True).start()
    
    def analysis_done(self, success, report_path):
        self.btn_run.config(state=tk.NORMAL, text="🚀 开始分析")
        if success and report_path and os.path.exists(report_path):
            self.report_path = report_path
            self.btn_open.config(state=tk.NORMAL)
            self.log(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📌 报告已生成！点击【打开报告】查看\n")
        else:
            self.log(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⚠️ 分析未完成，请检查日志\n")
    
    def open_report(self):
        if self.report_path and os.path.exists(self.report_path):
            try:
                webbrowser.open(os.path.abspath(self.report_path))
            except Exception as e:
                messagebox.showerror("错误", f"打开报告失败:\n{str(e)}")
        else:
            messagebox.showinfo("提示", "报告尚未生成，请先完成分析")
    
    def show_help(self):
        help_text = (
            "💡 使用指南\n\n"
            "1️⃣ 输入中文地名（如：上海外滩、深圳南山科技园）\n"
            "2️⃣ 点击【开始分析】或按回车键\n"
            "3️⃣ 查看日志区实时进度\n"
            "4️⃣ 完成后点击【打开报告】查看可视化结果\n\n"
        )
        messagebox.showinfo("帮助", help_text)

def main():
    root = tk.Tk()
    # 设置窗口居中（关键！解决"不方便"痛点）
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (700 // 2)
    y = (root.winfo_screenheight() // 2) - (500 // 2)
    root.geometry(f"700x500+{x}+{y}")
    
    # 设置应用图标（可选，无则忽略）
    try:
        root.iconbitmap(default='python.ico')  # 无此文件会自动跳过
    except:
        pass
    
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()