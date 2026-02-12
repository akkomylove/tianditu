"""
天地图数据分析工具 - GUI主界面
✅ 新增：瓦片类型选择、缩放等级选择
✅ 适配参数传递：用户地址/瓦片类型/缩放等级
✅ 输入校验：缩放等级1-18范围限制
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
# 导入项目核心模块
from config import (
    TIANDITU_TILE_TYPES, DEFAULT_TILE_TYPE,
    ZOOM_LEVEL_RANGE, DEFAULT_ZOOM_LEVEL, ZOOM_LEVEL_DESC,
    USER_QUERY_ADDRESS  # 用于传递用户地址
)
from geocoder import get_location_bounds
from image_fetcher import fetch_tiles
from image_merger import merge_tiles
from data_analyzer import analyze_tile_data
from visualization import generate_report

class TiandituAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("天地图地理数据分析工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # 初始化变量（绑定控件值）
        self.place_name_var = tk.StringVar()  # 用户输入的地址
        self.tile_type_var = tk.StringVar(value=DEFAULT_TILE_TYPE)  # 瓦片类型，默认矢量图
        self.zoom_level_var = tk.StringVar(value=str(DEFAULT_ZOOM_LEVEL))  # 缩放等级，默认12

        # 创建主布局
        self.create_widgets()

    def create_widgets(self):
        # ========== 顶部输入区域 ==========
        input_frame = ttk.LabelFrame(self.root, text="基础配置", padding=(10, 10))
        input_frame.pack(fill=tk.X, padx=20, pady=10)

        # 1. 地址输入行
        ttk.Label(input_frame, text="查询地址：").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        place_entry = ttk.Entry(input_frame, textvariable=self.place_name_var, width=50)
        place_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        # 地址输入提示
        ttk.Label(input_frame, text="示例：北京中关村/上海市浦东新区", font=("Arial", 8), foreground="gray").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)

        # 2. 瓦片类型选择行
        ttk.Label(input_frame, text="瓦片类型：").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        # 瓦片类型下拉框（选项来自config的TIANDITU_TILE_TYPES）
        tile_combobox = ttk.Combobox(
            input_frame,
            textvariable=self.tile_type_var,
            values=list(TIANDITU_TILE_TYPES.keys()),
            state="readonly",  # 仅允许选择，禁止手动输入
            width=47
        )
        tile_combobox.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        # 瓦片类型提示
        ttk.Label(input_frame, text="矢量图/影像图/地形/注记", font=("Arial", 8), foreground="gray").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        # 3. 缩放等级选择行
        ttk.Label(input_frame, text="缩放等级：").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        # 缩放等级下拉框（1-18，默认12）
        zoom_combobox = ttk.Combobox(
            input_frame,
            textvariable=self.zoom_level_var,
            values=[str(i) for i in range(ZOOM_LEVEL_RANGE[0], ZOOM_LEVEL_RANGE[1]+1)],
            state="readonly",  # 仅允许选择，避免手动输入无效值
            width=47
        )
        zoom_combobox.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        # 缩放等级提示
        zoom_tip = f"范围{ZOOM_LEVEL_RANGE[0]}-{ZOOM_LEVEL_RANGE[1]}，1=全球，18=街区级"
        ttk.Label(input_frame, text=zoom_tip, font=("Arial", 8), foreground="gray").grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)

        # 4. 开始分析按钮
        start_btn = ttk.Button(input_frame, text="开始分析", command=self.start_analysis)
        start_btn.grid(row=3, column=1, sticky=tk.W, padx=5, pady=10)

        # ========== 日志输出区域 ==========
        log_frame = ttk.LabelFrame(self.root, text="运行日志", padding=(10, 10))
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=90, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        """日志输出到文本框"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)  # 自动滚动到最后一行
        self.root.update_idletasks()  # 刷新界面

    def validate_inputs(self):
        """校验用户输入"""
        # 1. 地址不能为空
        place_name = self.place_name_var.get().strip()
        if not place_name:
            messagebox.showerror("输入错误", "查询地址不能为空！")
            return False
        # 2. 缩放等级必须是1-18的数字
        try:
            zoom_level = int(self.zoom_level_var.get())
            if not (ZOOM_LEVEL_RANGE[0] <= zoom_level <= ZOOM_LEVEL_RANGE[1]):
                raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", f"缩放等级必须是{ZOOM_LEVEL_RANGE[0]}-{ZOOM_LEVEL_RANGE[1]}的整数！")
            return False
        return True

    def start_analysis(self):
        """启动分析线程（避免界面卡死）"""
        if not self.validate_inputs():
            return
        # 清空日志
        self.log_text.delete(1.0, tk.END)
        # 启动后台线程执行分析
        analysis_thread = threading.Thread(target=self.run_analysis)
        analysis_thread.daemon = True  # 主线程退出时，子线程也退出
        analysis_thread.start()

    def run_analysis(self):
        """核心分析逻辑（后台线程执行）"""
        try:
            # 1. 获取用户输入的参数
            place_name = self.place_name_var.get().strip()
            tile_type = self.tile_type_var.get()  # 选中的瓦片类型（如"矢量图"）
            zoom_level = int(self.zoom_level_var.get())  # 选中的缩放等级
            self.log(f"📌 开始分析：地址={place_name} | 瓦片类型={tile_type} | 缩放等级={zoom_level}")

            # 2. 地理编码获取边界
            self.log("🔍 正在进行地理编码...")
            bounds, msg = get_location_bounds(place_name)
            if not bounds:
                self.log(f"❌ 地理编码失败：{msg}")
                messagebox.showerror("地理编码失败", msg)
                return
            self.log(f"✅ 地理编码成功：{msg}")

            # 3. 获取瓦片类型对应的URL模板
            tile_config = TIANDITU_TILE_TYPES[tile_type]
            tile_code = tile_config["code"]
            tile_url_template = tile_config["url_template"]
            self.log(f"📌 瓦片配置：类型={tile_type} | 标识={tile_code} | URL模板={tile_url_template[:50]}...")

            # 4. 下载瓦片
            self.log("📥 开始下载瓦片...")
            tile_paths = fetch_tiles(
                bounds=bounds,
                zoom_level=zoom_level,  # 传递动态缩放等级
                tile_url_template=tile_url_template  # 传递动态瓦片URL模板
            )
            if not tile_paths:
                self.log("❌ 瓦片下载失败！")
                messagebox.showerror("下载失败", "瓦片下载失败，请检查网络或密钥！")
                return
            self.log(f"✅ 瓦片下载完成，共{len(tile_paths)}个瓦片")

            # 5. 合并瓦片
            self.log("🖼️ 开始合并瓦片...")
            merged_image_path = merge_tiles(tile_paths, zoom_level=zoom_level)  # 传递缩放等级
            if not merged_image_path:
                self.log("❌ 瓦片合并失败！")
                messagebox.showerror("合并失败", "瓦片合并失败，请检查瓦片文件！")
                return
            self.log(f"✅ 瓦片合并完成：{merged_image_path}")

            # 6. 数据分析（后续重构为文化/交通分析）
            self.log("📊 正在进行文化/交通分析...")
            analysis_result = analyze_tile_data(
                tile_paths=tile_paths,
                bounds=bounds,
                place_name=place_name,  # 传递用户地址
                tile_type=tile_type,    # 传递瓦片类型
                zoom_level=zoom_level   # 传递缩放等级
            )
            if not analysis_result:
                self.log("⚠️ 数据分析结果为空")
            else:
                self.log(f"✅ 数据分析完成：{json.dumps(analysis_result, ensure_ascii=False, indent=2)}")

            # 7. 生成报告（嵌入用户地址、瓦片类型、缩放等级）
            self.log("📝 正在生成分析报告...")
            report_path = generate_report(
                analysis_result=analysis_result,
                place_name=place_name,
                tile_type=tile_type,
                zoom_level=zoom_level,
                bounds=bounds
            )
            if not report_path:
                self.log("❌ 报告生成失败！")
                messagebox.showerror("报告失败", "分析报告生成失败！")
                return
            self.log(f"✅ 报告生成完成：{report_path}")

            # 8. 完成提示
            self.log("\n🎉 所有分析流程完成！")
            messagebox.showinfo("分析完成", f"✅ 分析成功！\n📄 报告路径：{report_path}\n🖼️ 合并图片路径：{merged_image_path}")

        except Exception as e:
            error_msg = f"❌ 分析过程出错：{str(e)}"
            self.log(error_msg)
            messagebox.showerror("分析出错", error_msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = TiandituAnalyzerGUI(root)
    root.mainloop()