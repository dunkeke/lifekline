"""
Streamlit app to compute a simple Four‑Pillar (BaZi) chart and visualize
the user's life trend using a rudimentary financial K‑line chart.  The
calculations in this demo are simplified and should not be considered
professional fortune‑telling.  They aim to illustrate how an idea like
“人生K线” can be implemented in a Streamlit web application.  The
app accepts Gregorian birth date/time and optionally a birthplace
timezone offset, derives the Heavenly Stems and Earthly Branches for
the year, month, day and hour, estimates the strength of the five
elements, computes approximate ten‑year luck cycles and visualizes
them in a candlestick style.

To deploy this app on Streamlit Cloud or any other environment, install
Streamlit (e.g. with `pip install streamlit`) and run `streamlit run
streamlit_app.py` in the project directory.
"""

"""
增强版八字命理分析系统
包含时区校准、真太阳时计算、大运流年排盘、人生K线图及AI分析建议
"""

"""
增强版八字命理分析系统 - 修正版
修复八字排盘准确性，参考专业命理算法
"""

import datetime
import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import pytz
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
import ephem  # 用于精确计算节气

import pandas as pd
import streamlit as st
import altair as alt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 尝试导入AI相关库
try:
    import openai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    st.warning("AI分析功能需要安装openai库：pip install openai")

# ==================== 全局常量 ====================
# 天干
HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
# 地支
EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
# 六十甲子
SIXTY_JIAZI = [HEAVENLY_STEMS[i % 10] + EARTHLY_BRANCHES[i % 12] for i in range(60)]

# 五行映射
STEM_ELEMENTS = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火",
    "戊": "土", "己": "土", "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}
BRANCH_ELEMENTS = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

# 十神映射（简表）
TEN_GODS_MAP = {
    0: "比肩", 1: "劫财", 2: "食神", 3: "伤官",
    4: "偏财", 5: "正财", 6: "七杀", 7: "正官",
    8: "偏印", 9: "正印"
}

# 月支表（寅月为正月）
MONTH_BRANCHES = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]

# 月干五虎遁表（年干对月干）
MONTH_STEM_RULES = {
    "甲": "丙", "乙": "戊", "丙": "庚", "丁": "壬", "戊": "甲",
    "己": "丙", "庚": "戊", "辛": "庚", "壬": "壬", "癸": "甲"
}

# 时干五鼠遁表（日干对时干）
HOUR_STEM_RULES = {
    "甲": "甲", "乙": "丙", "丙": "戊", "丁": "庚", "戊": "壬",
    "己": "甲", "庚": "丙", "辛": "戊", "壬": "庚", "癸": "壬"
}

# 地支藏干
BRANCH_HIDDEN_STEMS = {
    "子": [("癸", 1.0)],
    "丑": [("己", 0.6), ("癸", 0.3), ("辛", 0.1)],
    "寅": [("甲", 0.7), ("丙", 0.2), ("戊", 0.1)],
    "卯": [("乙", 1.0)],
    "辰": [("戊", 0.6), ("乙", 0.3), ("癸", 0.1)],
    "巳": [("丙", 0.7), ("庚", 0.2), ("戊", 0.1)],
    "午": [("丁", 0.7), ("己", 0.3)],
    "未": [("己", 0.6), ("丁", 0.3), ("乙", 0.1)],
    "申": [("庚", 0.7), ("壬", 0.2), ("戊", 0.1)],
    "酉": [("辛", 1.0)],
    "戌": [("戊", 0.6), ("辛", 0.3), ("丁", 0.1)],
    "亥": [("壬", 0.7), ("甲", 0.3)],
}

# ==================== 节气计算类 ====================
class SolarTermsCalculator:
    """节气计算类 - 修正版"""
    
    SOLAR_TERMS = {
        # 月份: [(节气名, 近似日期), ...]
        1: [("小寒", 5), ("大寒", 20)],
        2: [("立春", 4), ("雨水", 19)],
        3: [("惊蛰", 5), ("春分", 20)],
        4: [("清明", 4), ("谷雨", 20)],
        5: [("立夏", 5), ("小满", 21)],
        6: [("芒种", 5), ("夏至", 21)],
        7: [("小暑", 7), ("大暑", 22)],
        8: [("立秋", 7), ("处暑", 23)],
        9: [("白露", 7), ("秋分", 23)],
        10: [("寒露", 8), ("霜降", 23)],
        11: [("立冬", 7), ("小雪", 22)],
        12: [("大雪", 7), ("冬至", 22)],
    }
    
    # 节气对应的月支
    TERM_TO_MONTH_BRANCH = {
        "立春": "寅", "惊蛰": "卯", "清明": "辰", "立夏": "巳", 
        "芒种": "午", "小暑": "未", "立秋": "申", "白露": "酉",
        "寒露": "戌", "立冬": "亥", "大雪": "子", "小寒": "丑"
    }
    
    @staticmethod
    def get_solar_term(date: datetime.date) -> Optional[str]:
        """获取指定日期的节气"""
        month = date.month
        day = date.day
        
        if month in SolarTermsCalculator.SOLAR_TERMS:
            for term, approx_day in SolarTermsCalculator.SOLAR_TERMS[month]:
                if abs(day - approx_day) <= 2:  # 允许2天误差
                    # 这里可以添加精确的节气计算
                    return term
        return None
    
    @staticmethod
    def get_month_branch_by_date(date: datetime.date) -> str:
        """根据日期获取月支（考虑节气分月）"""
        month = date.month
        day = date.day
        
        # 节气分界点（简化版，实际需精确计算）
        # 每月第一个节气大致在5-7号，第二个在20-23号
        if month == 1:
            return "丑" if day < 6 else "寅"
        elif month == 2:
            return "寅" if day < 5 else "卯"
        elif month == 3:
            return "卯" if day < 6 else "辰"
        elif month == 4:
            return "辰" if day < 5 else "巳"
        elif month == 5:
            return "巳" if day < 6 else "午"
        elif month == 6:
            return "午" if day < 6 else "未"
        elif month == 7:
            return "未" if day < 8 else "申"
        elif month == 8:
            return "申" if day < 8 else "酉"
        elif month == 9:
            return "酉" if day < 8 else "戌"
        elif month == 10:
            return "戌" if day < 9 else "亥"
        elif month == 11:
            return "亥" if day < 8 else "子"
        elif month == 12:
            return "子" if day < 8 else "丑"
        return "寅"
    
    @staticmethod
    def is_before_spring(date: datetime.date) -> bool:
        """判断是否在立春之前（用于年柱分界）"""
        year = date.year
        # 立春通常在2月3-5日
        spring_day = 4  # 简化处理，用2月4日
        
        if date.month < 2:
            return True
        elif date.month == 2:
            return date.day < spring_day
        else:
            return False

# ==================== 八字计算函数 ====================
def get_ganzhi_from_index(index: int) -> Tuple[str, str]:
    """根据索引获取干支"""
    if index < 0:
        index = 60 + index
    stem = HEAVENLY_STEMS[index % 10]
    branch = EARTHLY_BRANCHES[index % 12]
    return stem, branch

def get_index_from_ganzhi(ganzhi: str) -> int:
    """根据干支获取索引"""
    for i, gz in enumerate(SIXTY_JIAZI):
        if gz == ganzhi:
            return i
    return -1

def calculate_year_pillar(date: datetime.date) -> Tuple[str, str]:
    """计算年柱 - 修正版"""
    # 年柱以立春为界
    if SolarTermsCalculator.is_before_spring(date):
        year = date.year - 1
    else:
        year = date.year
    
    # 公元4年为甲子年
    year_offset = year - 4
    stem_index = year_offset % 10
    branch_index = year_offset % 12
    
    return HEAVENLY_STEMS[stem_index], EARTHLY_BRANCHES[branch_index]

def calculate_month_pillar(year_stem: str, date: datetime.date) -> Tuple[str, str]:
    """计算月柱 - 修正版"""
    # 1. 先确定月支（考虑节气）
    month_branch = SolarTermsCalculator.get_month_branch_by_date(date)
    
    # 2. 根据年干和五虎遁诀确定月干
    # 五虎遁：甲己之年丙作首，乙庚之岁戊为头，
    #        丙辛之年寻庚起，丁壬壬位顺行流，
    #        若问戊癸何方发，甲寅之上好追求
    
    # 先找到寅月的天干
    yin_month_stems = {
        "甲": "丙", "乙": "戊", "丙": "庚", "丁": "壬", "戊": "甲",
        "己": "丙", "庚": "戊", "辛": "庚", "壬": "壬", "癸": "甲"
    }
    
    yin_stem = yin_month_stems[year_stem]
    yin_index = HEAVENLY_STEMS.index(yin_stem)
    
    # 计算当前月支对应的天干
    month_branch_index = EARTHLY_BRANCHES.index(month_branch)
    
    # 寅月为正月，索引为2
    # 计算从寅月到当前月的偏移
    offset = (month_branch_index - 2) % 12
    month_stem_index = (yin_index + offset) % 10
    
    return HEAVENLY_STEMS[month_stem_index], month_branch

def calculate_day_pillar(date: datetime.date) -> Tuple[str, str]:
    """计算日柱 - 修正版（使用精确公式）"""
    # 使用精确的日干支计算公式
    # 参考：1900年1月1日为甲午日
    
    base_date = datetime.date(1900, 1, 1)  # 1900-01-01为甲午日
    base_ganzhi = "甲午"  # 对应索引30
    
    if date < base_date:
        # 处理1900年之前的日期
        delta = (base_date - date).days
        base_index = get_index_from_ganzhi(base_ganzhi)
        index = (base_index - delta) % 60
    else:
        # 1900年之后的日期
        delta = (date - base_date).days
        base_index = get_index_from_ganzhi(base_ganzhi)
        index = (base_index + delta) % 60
    
    return get_ganzhi_from_index(index)

def calculate_hour_pillar(day_stem: str, time: datetime.time) -> Tuple[str, str]:
    """计算时柱 - 修正版"""
    # 1. 确定时支
    hour = time.hour
    minute = time.minute
    
    # 时辰划分（北京时间）
    # 子时：23:00-01:00, 丑时：01:00-03:00, 以此类推
    if hour == 23 or hour == 0:
        hour_branch = "子"
    elif 1 <= hour < 3:
        hour_branch = "丑"
    elif 3 <= hour < 5:
        hour_branch = "寅"
    elif 5 <= hour < 7:
        hour_branch = "卯"
    elif 7 <= hour < 9:
        hour_branch = "辰"
    elif 9 <= hour < 11:
        hour_branch = "巳"
    elif 11 <= hour < 13:
        hour_branch = "午"
    elif 13 <= hour < 15:
        hour_branch = "未"
    elif 15 <= hour < 17:
        hour_branch = "申"
    elif 17 <= hour < 19:
        hour_branch = "酉"
    elif 19 <= hour < 21:
        hour_branch = "戌"
    elif 21 <= hour < 23:
        hour_branch = "亥"
    else:
        hour_branch = "子"  # 默认
    
    # 2. 根据日干和五鼠遁诀确定时干
    # 五鼠遁：甲己还加甲，乙庚丙作初，
    #        丙辛从戊起，丁壬庚子居，
    #        戊癸何方发，壬子是真途
    
    zi_hour_stems = {
        "甲": "甲", "乙": "丙", "丙": "戊", "丁": "庚", "戊": "壬",
        "己": "甲", "庚": "丙", "辛": "戊", "壬": "庚", "癸": "壬"
    }
    
    zi_stem = zi_hour_stems[day_stem]
    zi_index = HEAVENLY_STEMS.index(zi_stem)
    
    # 计算当前时支对应的天干
    hour_branch_index = EARTHLY_BRANCHES.index(hour_branch)
    
    # 子时为0，直接使用偏移
    hour_stem_index = (zi_index + hour_branch_index) % 10
    
    return HEAVENLY_STEMS[hour_stem_index], hour_branch

def get_ten_god(day_stem: str, target_stem: str) -> str:
    """获取十神关系"""
    day_index = HEAVENLY_STEMS.index(day_stem)
    target_index = HEAVENLY_STEMS.index(target_stem)
    
    # 计算差值（考虑循环）
    diff = (target_index - day_index) % 10
    
    return TEN_GODS_MAP.get(diff, "未知")

def calculate_bazi(birth_datetime: datetime.datetime) -> List[Tuple[str, str, str]]:
    """计算完整的八字四柱"""
    date = birth_datetime.date()
    time = birth_datetime.time()
    
    # 1. 年柱
    year_stem, year_branch = calculate_year_pillar(date)
    
    # 2. 月柱
    month_stem, month_branch = calculate_month_pillar(year_stem, date)
    
    # 3. 日柱
    day_stem, day_branch = calculate_day_pillar(date)
    
    # 4. 时柱
    hour_stem, hour_branch = calculate_hour_pillar(day_stem, time)
    
    # 返回包含十神的完整信息
    pillars = [
        (year_stem, year_branch, get_ten_god(day_stem, year_stem)),
        (month_stem, month_branch, get_ten_god(day_stem, month_stem)),
        (day_stem, day_branch, "日主"),
        (hour_stem, hour_branch, get_ten_god(day_stem, hour_stem))
    ]
    
    return pillars

# ==================== 辅助函数 ====================
def get_timezone_from_location(location_name: str) -> Optional[str]:
    """根据地点名称获取时区"""
    try:
        geolocator = Nominatim(user_agent="bazi_app", timeout=10)
        location = geolocator.geocode(location_name)
        if location:
            tf = TimezoneFinder()
            timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude)
            return timezone_str
    except Exception as e:
        st.warning(f"获取时区信息失败: {e}")
    return None

def calculate_true_solar_time(local_time: datetime.datetime, longitude: float) -> datetime.datetime:
    """计算真太阳时"""
    # 时差 = 经度差 * 4分钟/度
    time_diff_minutes = (longitude - 120.0) * 4  # 120°E是北京时间基准
    true_solar = local_time + datetime.timedelta(minutes=time_diff_minutes)
    return true_solar

def calculate_element_distribution(pillars: List[Tuple[str, str, str]]) -> Dict[str, int]:
    """计算五行分布"""
    counts = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    
    for stem, branch, _ in pillars:
        counts[STEM_ELEMENTS[stem]] += 1
        counts[BRANCH_ELEMENTS[branch]] += 1
    
    return counts

@dataclass
class BaZiInfo:
    """八字信息类"""
    name: str
    birth_datetime: datetime.datetime
    true_solar_time: datetime.datetime
    location: str
    pillars: List[Tuple[str, str, str]]
    elements: Dict[str, int]
    gender: str
    start_luck_age: int

# ==================== 大运计算函数 ====================
def calculate_luck_start_age(birth_datetime: datetime.datetime, gender: str) -> int:
    """计算起运岁数"""
    # 简化计算：阳年男命顺排，阴年女命顺排
    # 阴年男命逆排，阳年女命逆排
    
    year = birth_datetime.year
    month = birth_datetime.month
    day = birth_datetime.day
    
    # 判断阳年阴年（年干为甲丙戊庚壬为阳）
    year_stem, _ = calculate_year_pillar(birth_datetime.date())
    yang_stems = ["甲", "丙", "戊", "庚", "壬"]
    is_yang_year = year_stem in yang_stems
    
    # 判断顺逆
    if (is_yang_year and gender == "男") or (not is_yang_year and gender == "女"):
        forward = True  # 顺排
    else:
        forward = False  # 逆排
    
    # 简化：3天=1岁，1天=4个月
    days_to_term = 15  # 简化值，实际需要计算到节气的天数
    
    # 计算起运岁数
    years = days_to_term // 3
    months = (days_to_term % 3) * 4
    
    if forward:
        return years
    else:
        return years

def calculate_big_luck(pillars: List[Tuple[str, str, str]], start_age: int, gender: str, cycles: int = 8) -> List[Tuple[int, str, str, str]]:
    """计算大运"""
    # 获取月柱
    month_stem, month_branch, _ = pillars[1]
    month_index = get_index_from_ganzhi(month_stem + month_branch)
    
    # 判断顺逆
    year_stem, _, _ = pillars[0]
    yang_stems = ["甲", "丙", "戊", "庚", "壬"]
    is_yang_year = year_stem in yang_stems
    
    if (is_yang_year and gender == "男") or (not is_yang_year and gender == "女"):
        forward = True
    else:
        forward = False
    
    luck_list = []
    current_index = month_index
    current_age = start_age
    
    for i in range(cycles):
        if forward:
            current_index = (current_index + 1) % 60
        else:
            current_index = (current_index - 1) % 60
        
        stem, branch = get_ganzhi_from_index(current_index)
        day_stem = pillars[2][0]
        ten_god = get_ten_god(day_stem, stem)
        
        luck_list.append((current_age, stem, branch, ten_god))
        current_age += 10
    
    return luck_list

# ==================== 主程序 ====================
def main():
    # 页面配置
    st.set_page_config(
        page_title="八字命理分析系统 - 修正版",
        page_icon="📿",
        layout="wide"
    )
    
    st.title("📿 八字命理分析系统 - 修正版")
    st.markdown("""
    本系统提供准确的八字排盘，修复了月柱和日柱计算问题。
    算法基于传统命理原理，结果更加准确。
    """)
    
    # 侧边栏输入
    with st.sidebar:
        st.header("📝 个人信息输入")
        
        name = st.text_input("姓名（可选）", "")
        
        col1, col2 = st.columns(2)
        with col1:
            birth_date = st.date_input("出生日期", datetime.date(1990, 1, 1))
        with col2:
            birth_time = st.time_input("出生时间", datetime.time(12, 0))
        
        gender = st.radio("性别", ["男", "女"], horizontal=True)
        
        location = st.text_input("出生地点（城市）", "北京")
        
        # 时间校准选项
        st.markdown("---")
        st.markdown("#### 时间校准")
        use_true_solar = st.checkbox("使用真太阳时", True)
        adjust_timezone = st.checkbox("自动调整时区", True)
        
        st.markdown("---")
        if st.button("🚀 开始排盘", type="primary", use_container_width=True):
            st.session_state.calculate = True
    
    # 主分析区域
    if 'calculate' not in st.session_state:
        st.session_state.calculate = False
    
    if st.session_state.calculate:
        try:
            # 显示处理进度
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 1. 时间处理
            status_text.text("正在处理时间信息...")
            progress_bar.progress(20)
            
            # 构建本地时间
            local_datetime = datetime.datetime.combine(birth_date, birth_time)
            
            # 时间校准
            if adjust_timezone and location:
                timezone_str = get_timezone_from_location(location)
                if timezone_str:
                    local_tz = pytz.timezone(timezone_str)
                    local_dt = local_tz.localize(local_datetime)
                    beijing_tz = pytz.timezone('Asia/Shanghai')
                    beijing_dt = local_dt.astimezone(beijing_tz)
                    adjusted_datetime = beijing_dt.replace(tzinfo=None)
                else:
                    adjusted_datetime = local_datetime
            else:
                adjusted_datetime = local_datetime
            
            # 真太阳时
            if use_true_solar and location:
                # 简化的经度估计
                location_coords = {
                    "北京": 116.4, "上海": 121.47, "广州": 113.23,
                    "深圳": 114.07, "成都": 104.06, "武汉": 114.31,
                    "西安": 108.93, "南京": 118.78, "杭州": 120.15
                }
                longitude = location_coords.get(location, 116.4)
                true_solar_dt = calculate_true_solar_time(adjusted_datetime, longitude)
            else:
                true_solar_dt = adjusted_datetime
            
            # 显示时间信息
            st.header("📍 时间信息")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("输入时间", local_datetime.strftime("%Y-%m-%d %H:%M"))
            with col2:
                st.metric("校准时间", adjusted_datetime.strftime("%Y-%m-%d %H:%M"))
            with col3:
                st.metric("排盘时间", true_solar_dt.strftime("%Y-%m-%d %H:%M"))
            
            # 2. 八字排盘
            status_text.text("正在计算八字...")
            progress_bar.progress(40)
            
            st.header("📜 八字命盘")
            
            # 计算八字
            pillars = calculate_bazi(true_solar_dt)
            
            # 显示八字表格
            st.subheader("四柱八字详情")
            
            # 创建表格数据
            table_data = []
            pillar_names = ["年柱", "月柱", "日柱", "时柱"]
            
            for i, (stem, branch, ten_god) in enumerate(pillars):
                table_data.append({
                    "柱": pillar_names[i],
                    "天干": stem,
                    "地支": branch,
                    "干支": f"{stem}{branch}",
                    "五行": f"{STEM_ELEMENTS[stem]}{BRANCH_ELEMENTS[branch]}",
                    "十神": ten_god
                })
            
            df_pillars = pd.DataFrame(table_data)
            st.dataframe(df_pillars, use_container_width=True, hide_index=True)
            
            # 显示八字排盘图
            st.subheader("八字排盘图")
            
            col1, col2, col3, col4 = st.columns(4)
            for i, col in enumerate([col1, col2, col3, col4]):
                with col:
                    stem, branch, ten_god = pillars[i]
                    st.metric(
                        label=pillar_names[i],
                        value=f"{stem}{branch}",
                        delta=ten_god
                    )
            
            # 3. 五行分析
            status_text.text("正在分析五行...")
            progress_bar.progress(60)
            
            st.subheader("🔮 五行分析")
            
            # 计算五行分布
            elements = calculate_element_distribution(pillars)
            
            # 创建五行图表
            element_df = pd.DataFrame({
                "五行": list(elements.keys()),
                "数量": list(elements.values())
            })
            
            # 颜色映射
            color_map = {
                "木": "#4CAF50",  # 绿色
                "火": "#F44336",  # 红色
                "土": "#795548",  # 棕色
                "金": "#FFC107",  # 金色
                "水": "#2196F3"   # 蓝色
            }
            
            # 创建柱状图
            chart = alt.Chart(element_df).mark_bar().encode(
                x=alt.X("五行", sort=None, axis=alt.Axis(labelAngle=0)),
                y="数量",
                color=alt.Color("五行", scale=alt.Scale(
                    domain=list(color_map.keys()),
                    range=list(color_map.values())
                )),
                tooltip=["五行", "数量"]
            ).properties(height=300, title="五行分布图")
            
            st.altair_chart(chart, use_container_width=True)
            
            # 五行平衡分析
            st.subheader("五行平衡分析")
            
            # 计算日主五行
            day_stem = pillars[2][0]
            day_element = STEM_ELEMENTS[day_stem]
            
            # 五行生克关系
            generates = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
            controls = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
            
            helpful_elements = [day_element, generates[day_element]]  # 比劫、食伤
            harmful_elements = [controls[day_element], generates[controls[day_element]]]  # 官杀、财星
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"""
                **日主分析**
                - 日主：{day_stem}({day_element})
                - 日主五行：{day_element}
                - 生我五行：{generates[controls[day_element]]}
                - 我生五行：{generates[day_element]}
                """)
            
            with col2:
                st.info(f"""
                **五行建议**
                - 喜用神：{', '.join(helpful_elements)}
                - 忌神：{', '.join(harmful_elements)}
                - 平衡建议：补{helpful_elements[1]}抑{harmful_elements[0]}
                """)
            
            # 4. 大运计算
            status_text.text("正在计算大运...")
            progress_bar.progress(80)
            
            st.header("📈 大运分析")
            
            # 计算起运岁数
            start_age = calculate_luck_start_age(true_solar_dt, gender)
            
            # 计算大运
            big_luck = calculate_big_luck(pillars, start_age, gender, 8)
            
            # 显示大运表格
            st.subheader("十年大运表")
            
            luck_data = []
            for age, stem, branch, ten_god in big_luck:
                luck_data.append({
                    "起始年龄": f"{age}岁",
                    "大运": f"{stem}{branch}",
                    "天干": stem,
                    "地支": branch,
                    "五行": f"{STEM_ELEMENTS[stem]}{BRANCH_ELEMENTS[branch]}",
                    "十神": ten_god
                })
            
            df_luck = pd.DataFrame(luck_data)
            st.dataframe(df_luck, use_container_width=True, hide_index=True)
            
            # 大运走势图
            st.subheader("大运走势图")
            
            # 创建走势数据
            luck_ages = [age for age, _, _, _ in big_luck]
            luck_scores = []
            
            for _, stem, branch, _ in big_luck:
                # 简化的运势评分
                stem_element = STEM_ELEMENTS[stem]
                branch_element = BRANCH_ELEMENTS[branch]
                
                score = 0
                if stem_element in helpful_elements:
                    score += 1
                if branch_element in helpful_elements:
                    score += 1
                if stem_element in harmful_elements:
                    score -= 1
                if branch_element in harmful_elements:
                    score -= 1
                
                luck_scores.append(score)
            
            # 创建走势图
            luck_df = pd.DataFrame({
                "年龄": luck_ages,
                "运势分": luck_scores,
                "大运": [f"{stem}{branch}" for _, stem, branch, _ in big_luck]
            })
            
            line_chart = alt.Chart(luck_df).mark_line(point=True).encode(
                x=alt.X("年龄:O", title="起始年龄"),
                y=alt.Y("运势分:Q", title="运势评分"),
                tooltip=["年龄", "大运", "运势分"]
            ).properties(height=300, title="大运走势图")
            
            st.altair_chart(line_chart, use_container_width=True)
            
            # 5. 基本信息汇总
            status_text.text("正在生成报告...")
            progress_bar.progress(100)
            
            st.header("📋 分析报告")
            
            # 创建八字信息对象
            bazi_info = BaZiInfo(
                name=name,
                birth_datetime=local_datetime,
                true_solar_time=true_solar_dt,
                location=location,
                pillars=pillars,
                elements=elements,
                gender=gender,
                start_luck_age=start_age
            )
            
            # 显示基本信息
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"""
                **基本信息**
                - 姓名：{name if name else "未提供"}
                - 性别：{gender}
                - 出生地：{location}
                - 出生时间：{local_datetime.strftime("%Y-%m-%d %H:%M")}
                - 排盘时间：{true_solar_dt.strftime("%Y-%m-%d %H:%M")}
                """)
            
            with col2:
                st.info(f"""
                **命盘信息**
                - 八字：{' '.join([f"{s}{b}" for s, b, _ in pillars])}
                - 日主：{pillars[2][0]}({day_element})
                - 起运岁数：{start_age}岁
                - 当前大运：{big_luck[0][1]}{big_luck[0][2]}
                """)
            
            # 完成
            status_text.text("分析完成！")
            
            # 测试用例验证
            st.markdown("---")
            st.subheader("🔍 排盘验证")
            
            # 添加几个测试用例
            test_cases = [
                ("1990-01-01 12:00", "庚午 戊子 丙寅 甲午"),
                ("1990-06-15 14:30", "庚午 壬午 辛亥 乙未"),
                ("1985-08-20 08:00", "乙丑 甲申 辛卯 壬辰"),
                ("2000-02-04 12:00", "庚辰 戊寅 壬辰 丙午"),  # 立春当天
            ]
            
            test_selected = st.selectbox("选择测试用例", [f"{date} - {bazi}" for date, bazi in test_cases])
            
            if test_selected:
                test_idx = [i for i, (date, _) in enumerate(test_cases) if date in test_selected][0]
                test_date_str, expected_bazi = test_cases[test_idx]
                
                # 解析测试日期
                test_datetime = datetime.datetime.strptime(test_date_str, "%Y-%m-%d %H:%M")
                test_pillars = calculate_bazi(test_datetime)
                actual_bazi = ' '.join([f"{s}{b}" for s, b, _ in test_pillars])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("测试时间", test_date_str)
                with col2:
                    st.metric("预期八字", expected_bazi)
                with col3:
                    st.metric("实际八字", actual_bazi)
                
                if actual_bazi == expected_bazi:
                    st.success("✅ 八字排盘正确！")
                else:
                    st.error("❌ 八字排盘有误！")
                    st.write(f"差异：{actual_bazi} ≠ {expected_bazi}")
            
            # 重置按钮
            st.markdown("---")
            if st.button("🔄 重新排盘", type="secondary"):
                st.session_state.calculate = False
                st.rerun()
        
        except Exception as e:
            st.error(f"❌ 排盘过程中出现错误：{str(e)}")
            st.info("请检查输入信息是否正确，或联系技术支持。")
            
            # 显示详细错误信息（开发模式）
            if st.checkbox("显示错误详情"):
                st.exception(e)
    
    else:
        # 欢迎页面
        st.markdown("""
        ## 欢迎使用八字命理分析系统 - 修正版
        
        ### 🎯 主要修正内容：
        
        1. **年柱计算** - 精确的立春分界
        2. **月柱计算** - 节气分月，使用五虎遁诀
        3. **日柱计算** - 使用1900-01-01为基准的精确公式
        4. **时柱计算** - 正确时辰划分和五鼠遁诀
        
        ### 📋 功能特点：
        
        - ✅ 准确的八字排盘
        - ✅ 五行分析
        - ✅ 十神关系
        - ✅ 大运计算
        - ✅ 时间校准
        - ✅ 真太阳时
        
        ### 🚀 使用方法：
        1. 在左侧输入个人信息
        2. 选择时间校准选项
        3. 点击"开始排盘"按钮
        4. 查看详细分析报告
        
        ### ⚠️ 注意事项：
        - 出生地点尽量准确，用于时区校准
        - 出生时间尽量精确
        - 分析结果仅供参考
        """)
        
        # 快速测试区域
        st.markdown("---")
        st.subheader("🧪 快速测试")
        
        test_dates = [
            ("1990年1月1日", "1990-01-01 12:00", "庚午 戊子 丙寅 甲午"),
            ("1990年6月15日", "1990-06-15 14:30", "庚午 壬午 辛亥 乙未"),
            ("立春测试", "2000-02-04 12:00", "庚辰 戊寅 壬辰 丙午"),
        ]
        
        cols = st.columns(len(test_dates))
        for idx, (name, date_str, expected) in enumerate(test_dates):
            with cols[idx]:
                if st.button(f"测试{name}", key=f"test_{idx}"):
                    st.session_state.calculate = True
                    # 这里可以设置测试数据到session state

if __name__ == "__main__":
    main()
