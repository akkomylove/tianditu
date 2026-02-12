import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import sys
import webbrowser
from datetime import datetime
# 核心工具导入
from utils import generate_operation_id, create_unique_output_dir, get_file_size
from data_validator import (
    validate_operation_id, validate_coords, 
    validate_zoom_level, validate_file_path, validate_numeric
)
from db_utils import db, logger
from history_query import (
    query_history_records, delete_history_record, get_record_detail
)
# 配置和业务模块导入
from config import (
    TIANDITU_TILE_TYPES, ZOOM_LEVEL_RANGE, ZOOM_LEVEL_DESC,
    DEFAULT_TILE_TYPE, DEFAULT_ZOOM_LEVEL, OUTPUT_DIR
)
from geocoder import get_location_bounds
from image_fetcher import download_tiles
from image_merger import merge_tiles
from data_analyzer import (
    analyze_traffic, analyze_culture,
    analyze_life, analyze_commercial,
    analyze_education, analyze_medical
)
from visualization import generate_report

class TiandituAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("天地图交通&文化分析工具 V1.0")
        self.root.geometry("1000x800")
        
        # 初始化变量
        self.place_name_var = tk.StringVar()
        self.tile_type_var = tk.StringVar(value=DEFAULT_TILE_TYPE)
        self.zoom_level_var = tk.StringVar(value=str(DEFAULT_ZOOM_LEVEL))
        self.current_operation_id = None
        self.current_output_dir = None
        
        # 历史记录筛选变量
        self.history_op_id_var = tk.StringVar()
        self.history_place_var = tk.StringVar()
        self.history_status_var = tk.StringVar(value="all")
        
        # 创建主标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标签页1：分析操作
        self.analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_frame, text="分析操作")
        self.create_analysis_widgets()
        
        # 标签页2：历史记录
        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text="历史记录")
        self.create_history_widgets()
        
        # 初始化历史记录表格
        self.refresh_history_table()

    # ===================== 分析操作UI =====================
    def create_analysis_widgets(self):
        # 1. 输入区域
        input_frame = ttk.LabelFrame(self.analysis_frame, text="输入参数")
        input_frame.pack(padx=10, pady=10, fill=tk.X)
        
        # 地址输入
        ttk.Label(input_frame, text="查询地址：").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        addr_entry = ttk.Entry(input_frame, textvariable=self.place_name_var, width=50)
        addr_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 瓦片类型选择
        ttk.Label(input_frame, text="瓦片类型：").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        tile_combo = ttk.Combobox(input_frame, textvariable=self.tile_type_var, 
                                 values=list(TIANDITU_TILE_TYPES.keys()), state="readonly")
        tile_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 缩放等级选择
        ttk.Label(input_frame, text="缩放等级：").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        zoom_options = self._get_zoom_level_options()
        zoom_combo = ttk.Combobox(input_frame, textvariable=self.zoom_level_var, 
                                 values=zoom_options, state="readonly")
        zoom_combo.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 2. 按钮区域
        btn_frame = ttk.Frame(self.analysis_frame)
        btn_frame.pack(padx=10, pady=5, fill=tk.X)
        
        start_btn = ttk.Button(btn_frame, text="开始分析", command=self.start_analysis)
        start_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = ttk.Button(btn_frame, text="清空日志", command=self.clear_log)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 3. 日志区域
        log_frame = ttk.LabelFrame(self.analysis_frame, text="运行日志")
        log_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        # 日志颜色标签初始化
        self.log_text.tag_config("info", foreground="black")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("success", foreground="green")

    # ===================== 适配区间式ZOOM_LEVEL_DESC的辅助函数 =====================
    def _get_zoom_level_options(self):
        zoom_options = []
        for z in ZOOM_LEVEL_RANGE:
            desc = "未知等级"
            for range_key, range_desc in ZOOM_LEVEL_DESC.items():
                try:
                    clean_key = str(range_key).strip()
                    if not clean_key:
                        continue
                    key_parts = clean_key.split("-")
                    if len(key_parts) == 1:
                        r_val = int(key_parts[0])
                        if z == r_val:
                            desc = range_desc
                            break
                    elif len(key_parts) == 2:
                        r_min_str, r_max_str = key_parts[0].strip(), key_parts[1].strip()
                        if not r_min_str or not r_max_str:
                            continue
                        r_min, r_max = int(r_min_str), int(r_max_str)
                        if r_min <= z <= r_max:
                            desc = range_desc
                            break
                except (ValueError, TypeError):
                    continue
            zoom_options.append(f"{z} - {desc}")
        return zoom_options

    # ===================== 历史记录UI =====================
    def create_history_widgets(self):
        # 1. 筛选区域
        filter_frame = ttk.LabelFrame(self.history_frame, text="筛选条件")
        filter_frame.pack(padx=10, pady=10, fill=tk.X)
        
        # 操作ID筛选
        ttk.Label(filter_frame, text="操作ID：").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        op_id_entry = ttk.Entry(filter_frame, textvariable=self.history_op_id_var, width=20)
        op_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 地址筛选
        ttk.Label(filter_frame, text="查询地址：").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        place_entry = ttk.Entry(filter_frame, textvariable=self.history_place_var, width=20)
        place_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # 状态筛选
        ttk.Label(filter_frame, text="操作状态：").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        status_combo = ttk.Combobox(filter_frame, textvariable=self.history_status_var, 
                                   values=["all", "success", "failed", "running"], state="readonly")
        status_combo.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        
        # 筛选按钮
        query_btn = ttk.Button(filter_frame, text="查询", command=self.refresh_history_table)
        query_btn.grid(row=0, column=6, padx=5, pady=5)
        
        reset_btn = ttk.Button(filter_frame, text="重置", command=self.reset_history_filter)
        reset_btn.grid(row=0, column=7, padx=5, pady=5)
        
        # 2. 操作按钮区域
        btn_frame = ttk.Frame(self.history_frame)
        btn_frame.pack(padx=10, pady=5, fill=tk.X)
        
        view_report_btn = ttk.Button(btn_frame, text="查看报告", command=self.view_selected_report)
        view_report_btn.pack(side=tk.LEFT, padx=5)
        
        open_dir_btn = ttk.Button(btn_frame, text="打开文件夹", command=self.open_selected_dir)
        open_dir_btn.pack(side=tk.LEFT, padx=5)
        
        delete_btn = ttk.Button(btn_frame, text="删除记录", command=self.delete_selected_record)
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        # 3. 历史记录表格
        table_frame = ttk.LabelFrame(self.history_frame, text="历史操作记录")
        table_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # 创建表格
        columns = ("operation_id", "place_name", "status", "create_time", "output_dir")
        self.history_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        # 设置表头
        self.history_tree.heading("operation_id", text="操作ID")
        self.history_tree.heading("place_name", text="查询地址")
        self.history_tree.heading("status", text="状态")
        self.history_tree.heading("create_time", text="创建时间")
        self.history_tree.heading("output_dir", text="输出目录")
        
        # 设置列宽
        self.history_tree.column("operation_id", width=200)
        self.history_tree.column("place_name", width=150)
        self.history_tree.column("status", width=80)
        self.history_tree.column("create_time", width=180)
        self.history_tree.column("output_dir", width=300)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # ===================== 历史记录操作方法 =====================
    def refresh_history_table(self):
        """刷新历史记录表格"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        op_id = self.history_op_id_var.get().strip()
        place_name = self.history_place_var.get().strip()
        status = self.history_status_var.get() if self.history_status_var.get() != "all" else None
        
        records = query_history_records(
            operation_id=op_id,
            place_name=place_name,
            status=status
        )
        
        if not isinstance(records, list):
            records = []
        
        for record in records:
            self.history_tree.insert("", tk.END, values=(
                record["operation_id"],
                record["place_name"],
                record["status"],
                record["create_time"],
                record["output_dir"]
            ))
        
        self.log(f"✅ 历史记录刷新完成，共{len(records)}条", "success")

    def reset_history_filter(self):
        """重置筛选条件"""
        self.history_op_id_var.set("")
        self.history_place_var.set("")
        self.history_status_var.set("all")
        self.refresh_history_table()

    def get_selected_record(self):
        """获取选中的记录"""
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先选择一条历史记录！")
            return None
        item = self.history_tree.item(selected[0])
        operation_id = item["values"][0]
        output_dir = item["values"][4]
        return {"operation_id": operation_id, "output_dir": output_dir}

    def view_selected_report(self):
        """查看选中记录的报告"""
        record = self.get_selected_record()
        if not record:
            return
        
        detail = get_record_detail(record["operation_id"])
        if not detail or not detail.get("report_path"):
            messagebox.showwarning("提示", "该记录无可用的分析报告！")
            return
        
        report_path = detail["report_path"]
        if os.path.exists(report_path):
            webbrowser.open(f"file://{os.path.abspath(report_path)}")
            self.log(f"✅ 打开报告：{report_path}", "success")
        else:
            messagebox.showwarning("提示", "报告文件不存在！")

    def open_selected_dir(self):
        """打开选中记录的输出文件夹"""
        record = self.get_selected_record()
        if not record:
            return
        
        output_dir = record["output_dir"]
        if os.path.exists(output_dir):
            if sys.platform == "win32":
                os.startfile(output_dir)
            else:
                import subprocess
                subprocess.run(["open", output_dir])
            self.log(f"✅ 打开文件夹：{output_dir}", "success")
        else:
            messagebox.showwarning("提示", "输出文件夹不存在！")

    def delete_selected_record(self):
        """删除选中的记录"""
        record = self.get_selected_record()
        if not record:
            return
        
        confirm = messagebox.askyesno("确认", f"是否删除操作ID为【{record['operation_id']}】的记录？\n（包含数据库记录和输出文件夹）")
        if not confirm:
            return
        
        success = delete_history_record(record["operation_id"], delete_files=True)
        if success:
            messagebox.showinfo("成功", "记录删除成功！")
            self.refresh_history_table()
            self.log(f"✅ 删除记录：{record['operation_id']}", "success")
        else:
            messagebox.showerror("错误", "记录删除失败！")

    # ===================== 日志/基础方法 =====================
    def log(self, msg, level="info"):
        """日志输出（带颜色/级别）"""
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        self.log_text.tag_add(level, tk.END+"-2l", tk.END+"-1l")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)

    # ===================== 核心分析方法 =====================
    def start_analysis(self):
        """启动分析（多线程避免界面卡死）"""
        place_name = self.place_name_var.get().strip()
        tile_type = self.tile_type_var.get()
        zoom_level_str = self.zoom_level_var.get()
        
        if not place_name:
            messagebox.showerror("错误", "查询地址不能为空！")
            return
        
        # 解析缩放等级
        try:
            zoom_level = int(zoom_level_str.split(" - ")[0])
            if zoom_level not in ZOOM_LEVEL_RANGE:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", f"缩放等级必须是{ZOOM_LEVEL_RANGE}中的整数！")
            return
        
        # 多线程执行
        thread = threading.Thread(target=self.run_analysis, args=(place_name, tile_type, zoom_level))
        thread.daemon = True
        thread.start()

    def run_analysis(self, place_name, tile_type, zoom_level):
        """核心分析逻辑"""
        try:
            # 生成操作ID
            self.current_operation_id = generate_operation_id()
            if not validate_operation_id(self.current_operation_id):
                self.log("❌ operation_id格式错误，终止流程！", "error")
                return
            
            # 创建输出目录
            self.current_output_dir = create_unique_output_dir(self.current_operation_id)
            if not self.current_output_dir:
                self.log("❌ 创建输出目录失败，终止流程！", "error")
                return
            self.log(f"✅ 生成唯一操作ID：{self.current_operation_id}", "success")
            self.log(f"✅ 创建输出文件夹：{self.current_output_dir}", "success")
            
            # 地理编码
            self.log("🔍 开始地理编码（地址→经纬度）...")
            geo_result = get_location_bounds(place_name)
            if not geo_result or len(geo_result) != 2:
                self.log("❌ 地理编码失败：返回值无效", "error")
                return
            bounds, geo_msg = geo_result
            if not bounds:
                self.log(f"❌ 地理编码失败：{geo_msg}", "error")
                return
            min_lon, max_lon = bounds["min_lon"], bounds["max_lon"]
            min_lat, max_lat = bounds["min_lat"], bounds["max_lat"]
            
            # 经纬度校验
            if not validate_coords(min_lon, max_lon, min_lat, max_lat):
                self.log("❌ 经纬度范围无效（非中国境内），终止流程！", "error")
                return
            self.log(f"✅ 地理编码成功：{geo_msg}", "success")
            
            # 写入操作主表
            self.log("📝 写入操作主记录到数据库...")
            current_time = db.get_current_time()
            insert_params = (
                self.current_operation_id,
                place_name,
                tile_type,
                zoom_level,
                min_lon,
                max_lon,
                min_lat,
                max_lat,
                self.current_output_dir,
                "running",
                current_time,
                current_time
            )
            insert_sql = """
            INSERT INTO tianditu_operations 
            (operation_id, place_name, tile_type, zoom_level, min_lon, max_lon, min_lat, max_lat, output_dir, status, create_time, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            insert_result = db.execute(insert_sql, insert_params, commit=True)
            if insert_result is None:
                self.log("⚠️ 操作主记录写入数据库失败（文件生成不受影响）", "warning")
            else:
                self.log("✅ 操作主记录写入数据库成功", "success")
            
            # 下载瓦片
            self.log("🌐 开始下载瓦片...")
            tiles_dir = os.path.join(self.current_output_dir, "tiles")
            validate_file_path(tiles_dir, must_exist=False)
            download_success = download_tiles(
                min_lon=min_lon, max_lon=max_lon,
                min_lat=min_lat, max_lat=max_lat,
                zoom_level=zoom_level,
                tile_type=tile_type,
                output_dir=tiles_dir,
                operation_id=self.current_operation_id
            )
            if not download_success:
                self.log("❌ 瓦片下载失败！", "error")
                self.update_operation_status("failed")
                return
            self.log("✅ 瓦片下载完成", "success")
            
            # 拼接瓦片
            self.log("🖼️ 开始拼接瓦片...")
            merged_path = os.path.join(self.current_output_dir, "merged_map.jpg")
            validate_file_path(merged_path, must_exist=False)
            merge_success = merge_tiles(
                tiles_dir=tiles_dir,
                zoom_level=zoom_level,
                output_path=merged_path,
                operation_id=self.current_operation_id
            )
            if not merge_success:
                self.log("❌ 瓦片拼接失败！", "error")
                self.update_operation_status("failed")
                return
            if validate_file_path(merged_path, must_exist=True):
                self.log("✅ 瓦片拼接完成，文件校验通过", "success")
            else:
                self.log("⚠️ 瓦片拼接完成，但文件不存在", "warning")
            
            # 分析+报告写入（事务控制）
            self.log("📊 开始POI数据分析+报告生成（事务控制）...")
            analysis_report_success = self.run_analysis_report_with_transaction(
                min_lon, max_lon, min_lat, max_lat, place_name, tile_type, zoom_level, bounds
            )
            if not analysis_report_success:
                self.log("❌ 分析+报告写入失败！", "error")
                self.update_operation_status("failed")
                return
            self.log("✅ POI数据分析+报告生成完成", "success")
            
            # 更新状态+刷新历史记录
            self.update_operation_status("success")
            self.refresh_history_table()
            
            # 最终提示
            self.log(f"🎉 全流程分析完成！\n- 操作ID：{self.current_operation_id}\n- 输出目录：{self.current_output_dir}", "success")
            messagebox.showinfo("成功", f"分析完成！\n输出目录：{self.current_output_dir}")
            
        except Exception as e:
            self.log(f"❌ 分析流程异常：{str(e)}", "error")
            self.update_operation_status("failed")
            messagebox.showerror("错误", f"分析失败：{str(e)}")

    def run_analysis_report_with_transaction(self, min_lon, max_lon, min_lat, max_lat, place_name, tile_type, zoom_level, bounds):
        """事务包裹：分析结果写入 + 报告生成 + 报告写入"""
        try:
            if not db.conn:
                raise Exception("数据库连接未初始化，无法开启事务")
            db.execute("BEGIN TRANSACTION", commit=False)
            
            # 调用所有6大类分析模块
            traffic_analysis = analyze_traffic(
                min_lon=min_lon, max_lon=max_lon,
                min_lat=min_lat, max_lat=max_lat,
                operation_id=self.current_operation_id
            )
            life_analysis = analyze_life(
                min_lon=min_lon, max_lon=max_lon,
                min_lat=min_lat, max_lat=max_lat,
                operation_id=self.current_operation_id
            )
            commercial_analysis = analyze_commercial(
                min_lon=min_lon, max_lon=max_lon,
                min_lat=min_lat, max_lat=max_lat,
                operation_id=self.current_operation_id
            )
            education_analysis = analyze_education(
                min_lon=min_lon, max_lon=max_lon,
                min_lat=min_lat, max_lat=max_lat,
                operation_id=self.current_operation_id
            )
            medical_analysis = analyze_medical(
                min_lon=min_lon, max_lon=max_lon,
                min_lat=min_lat, max_lat=max_lat,
                operation_id=self.current_operation_id
            )
            culture_analysis = analyze_culture(
                min_lon=min_lon, max_lon=max_lon,
                min_lat=min_lat, max_lat=max_lat,
                operation_id=self.current_operation_id
            )
            
            # 整合所有分析结果
            analysis_result = {
                "basic_info": {"place_name": place_name, "tile_type": tile_type, "zoom_level": zoom_level, "bounds": bounds},
                "traffic_analysis": traffic_analysis,
                "life_analysis": life_analysis,
                "commercial_analysis": commercial_analysis,
                "education_analysis": education_analysis,
                "medical_analysis": medical_analysis,
                "culture_analysis": culture_analysis,
            }
            
            # 生成综合洞察（关键：调用类内的generate_insights方法）
            analysis_result["insights"] = self.generate_insights(analysis_result)
            
            # 生成报告
            report_path = os.path.join(self.current_output_dir, "analysis_report.html")
            validate_file_path(report_path, must_exist=False)
            report_success = generate_report(
                analysis_result=analysis_result,
                place_name=place_name,
                tile_type=tile_type,
                zoom_level=zoom_level,
                bounds=bounds,
                output_path=report_path,
                operation_id=self.current_operation_id
            )
            if not report_success:
                raise Exception("报告生成失败")
            if not validate_file_path(report_path, must_exist=True):
                raise Exception("报告文件不存在")
            
            if db.conn:
                db.conn.commit()
            logger.info("✅ 分析+报告写入事务提交成功")
            return True
        except Exception as e:
            if db.conn:
                db.conn.rollback()
            logger.error(f"❌ 分析+报告写入事务回滚：{str(e)}", exc_info=True)
            self.log(f"⚠️ 分析+报告写入失败（事务回滚）：{str(e)}", "warning")
            return False

    # ===================== 修复：新增缺失的update_operation_status方法 =====================
    def update_operation_status(self, status):
        """更新操作状态（修复AttributeError核心方法）"""
        if not self.current_operation_id:
            return
        update_time = db.get_current_time()
        update_sql = """
        UPDATE tianditu_operations 
        SET status = ?, update_time = ? 
        WHERE operation_id = ?
        """
        update_result = db.execute(update_sql, (status, update_time, self.current_operation_id), commit=True)
        if update_result is None:
            self.log(f"⚠️ 操作状态（{status}）写入数据库失败", "warning")
        else:
            self.log(f"✅ 操作状态更新为：{status}", "success")

    # ===================== 修复：新增缺失的generate_insights方法 =====================
    def generate_insights(self, analysis_result):
        """生成综合洞察（扩展至6大类分析，修复AttributeError核心方法）"""
        place_name = analysis_result["basic_info"]["place_name"]
        
        # 提取各类评分
        traffic_score = analysis_result["traffic_analysis"].get("traffic_convenience_score", 0.0)
        life_score = analysis_result["life_analysis"].get("life_convenience_score", 0.0)
        commercial_score = analysis_result["commercial_analysis"].get("commercial_activity_score", 0.0)
        education_score = analysis_result["education_analysis"].get("education_support_score", 0.0)
        medical_score = analysis_result["medical_analysis"].get("medical_support_score", 0.0)
        culture_score = analysis_result["culture_analysis"].get("culture_feature_score", 0.0)
        
        # 综合评分
        total_score = traffic_score + life_score + commercial_score + education_score + medical_score + culture_score
        avg_score = round(total_score / 6, 1)
        
        insights = [
            f"{place_name}综合配套评分为{avg_score}分（满分10分），{'配套完善' if avg_score >= 7 else '配套一般' if avg_score >= 4 else '配套薄弱'}",
            f"交通便利度：{traffic_score:.1f}分，{'出行便利' if traffic_score >= 7 else '出行一般' if traffic_score >= 4 else '出行不便'}",
            f"生活便利度：{life_score:.1f}分，{'日常便利' if life_score >= 7 else '日常一般' if life_score >= 4 else '日常不便'}",
            f"商业活跃度：{commercial_score:.1f}分，{'商业繁荣' if commercial_score >= 7 else '商业一般' if commercial_score >= 4 else '商业冷清'}",
            f"教育配套：{education_score:.1f}分，{'教育资源丰富' if education_score >= 7 else '教育资源一般' if education_score >= 4 else '教育资源匮乏'}",
            f"医疗配套：{medical_score:.1f}分，{'医疗资源充足' if medical_score >= 7 else '医疗资源一般' if medical_score >= 4 else '医疗资源不足'}",
            f"文化特色：{culture_score:.1f}分，{'文化氛围浓厚' if culture_score >= 7 else '文化氛围一般' if culture_score >= 4 else '文化氛围淡薄'}",
            f"分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        # 交叉洞察（可选）
        traffic_density = analysis_result["traffic_analysis"].get("traffic_density_per_sqkm", 0.0)
        commercial_density = analysis_result["commercial_analysis"].get("commercial_density_per_sqkm", 0.0)
        if traffic_density > 0 and commercial_density > 0:
            corr = round(min(traffic_density, commercial_density) / max(traffic_density, commercial_density), 2)
            if corr >= 0.7:
                insights.insert(1, f"交通与商业配套关联性强（相关系数{corr}），出行便利度高的区域商业活跃度也高")
        
        return insights

# ===================== 主程序 =====================
if __name__ == "__main__":
    # 初始化数据库
    from init_db import create_tables
    create_tables()
    
    # 启动GUI
    root = tk.Tk()
    app = TiandituAnalyzerGUI(root)
    root.mainloop()
    
    # 程序退出时关闭数据库连接
    db.close()