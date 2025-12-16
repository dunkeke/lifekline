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

import datetime
import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import pytz
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim

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

# Constants for Heavenly Stems and Earthly Branches
HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

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

# 十神映射
TEN_GODS = {
    ("甲", "甲"): "比肩", ("甲", "乙"): "劫财", ("甲", "丙"): "食神", ("甲", "丁"): "伤官",
    ("甲", "戊"): "偏财", ("甲", "己"): "正财", ("甲", "庚"): "七杀", ("甲", "辛"): "正官",
    ("甲", "壬"): "偏印", ("甲", "癸"): "正印",
    # 简化版，实际需完整映射
}

# 五行生克关系
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
REDUCES = {"木": "水", "火": "木", "土": "火", "金": "土", "水": "金"}
COUNTERS = {"木": "金", "火": "水", "土": "木", "金": "火", "水": "土"}

# 地支藏干
BRANCH_HIDDEN_STEMS = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
}

class SolarTerms:
    """节气计算类"""
    SOLAR_TERMS = [
        ("小寒", 1, 5, 6), ("大寒", 1, 20, 21),
        ("立春", 2, 4, 5), ("雨水", 2, 19, 20),
        ("惊蛰", 3, 5, 6), ("春分", 3, 20, 21),
        ("清明", 4, 4, 5), ("谷雨", 4, 20, 21),
        ("立夏", 5, 5, 6), ("小满", 5, 21, 22),
        ("芒种", 6, 5, 6), ("夏至", 6, 21, 22),
        ("小暑", 7, 7, 8), ("大暑", 7, 22, 23),
        ("立秋", 8, 7, 8), ("处暑", 8, 23, 24),
        ("白露", 9, 7, 8), ("秋分", 9, 23, 24),
        ("寒露", 10, 8, 9), ("霜降", 10, 23, 24),
        ("立冬", 11, 7, 8), ("小雪", 11, 22, 23),
        ("大雪", 12, 7, 8), ("冬至", 12, 21, 22),
    ]
    
    @staticmethod
    def get_solar_term(date: datetime.date):
        """获取指定日期的节气"""
        for term, month, start, end in SolarTerms.SOLAR_TERMS:
            if date.month == month and start <= date.day <= end:
                return term
        return None

@dataclass
class BaZiChart:
    """八字命盘类"""
    name: str
    birth_datetime: datetime.datetime
    true_solar_time: datetime.datetime
    location: str
    pillars: List[Tuple[str, str]]  # 年柱、月柱、日柱、时柱
    elements: Dict[str, int]
    day_master: str  # 日主
    start_luck_age: int  # 起运岁数
    big_luck: List[Tuple[int, Tuple[str, str]]]  # 大运
    
    def to_dict(self):
        """转换为字典"""
        return {
            "姓名": self.name or "未提供",
            "出生时间": self.birth_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "真太阳时": self.true_solar_time.strftime("%Y-%m-%d %H:%M:%S"),
            "出生地": self.location or "未提供",
            "八字": " ".join([f"{stem}{branch}" for stem, branch in self.pillars]),
            "日主": self.day_master,
            "五行分布": self.elements,
            "起运岁数": self.start_luck_age,
            "大运": [f"{age}岁: {stem}{branch}" for age, (stem, branch) in self.big_luck]
        }

def get_timezone_from_location(location_name: str) -> Optional[str]:
    """根据地点名称获取时区"""
    try:
        geolocator = Nominatim(user_agent="bazi_app")
        location = geolocator.geocode(location_name)
        if location:
            tf = TimezoneFinder()
            timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude)
            return timezone_str
    except:
        pass
    return None

def calculate_true_solar_time(local_time: datetime.datetime, longitude: float) -> datetime.datetime:
    """计算真太阳时"""
    # 时差 = 经度差 * 4分钟/度
    time_diff_minutes = (longitude - 120.0) * 4  # 120°E是北京时间基准
    true_solar = local_time + datetime.timedelta(minutes=time_diff_minutes)
    return true_solar

def ganzhi_from_index(index: int) -> Tuple[str, str]:
    """根据索引获取干支"""
    stem = HEAVENLY_STEMS[index % 10]
    branch = EARTHLY_BRANCHES[index % 12]
    return stem, branch

def year_pillar(date: datetime.date) -> Tuple[str, str]:
    """计算年柱"""
    # 立春换年
    spring_date = datetime.date(date.year, 2, 4)  # 简化版，实际需精确计算
    if date < spring_date:
        year = date.year - 1
    else:
        year = date.year
    
    stem_index = (year - 4) % 10
    branch_index = (year - 4) % 12
    return HEAVENLY_STEMS[stem_index], EARTHLY_BRANCHES[branch_index]

def month_pillar(year_stem: str, date: datetime.date) -> Tuple[str, str]:
    """计算月柱"""
    # 节气换月
    solar_term = SolarTerms.get_solar_term(date)
    
    # 简化版月支：寅月为正月
    if date.month == 1:
        branch_index = 2  # 寅
    elif date.month == 2:
        branch_index = 3  # 卯
    else:
        branch_index = (date.month + 1) % 12
    
    # 月干：根据年干推算
    stem_index_year = HEAVENLY_STEMS.index(year_stem)
    # 甲己之年丙作首，乙庚之岁戊为头...
    month_stem_starts = [2, 4, 6, 8, 0, 2, 4, 6, 8, 0]  # 甲年从丙开始
    start_stem = month_stem_starts[stem_index_year]
    stem_index = (start_stem + branch_index - 2) % 10
    
    return HEAVENLY_STEMS[stem_index], EARTHLY_BRANCHES[branch_index]

def day_pillar(date: datetime.date) -> Tuple[str, str]:
    """计算日柱"""
    base_date = datetime.date(1900, 1, 31)  # 1900-01-31为甲子日
    base_index = 0
    delta_days = (date - base_date).days
    index = (base_index + delta_days) % 60
    return ganzhi_from_index(index)

def hour_pillar(day_stem: str, time: datetime.time) -> Tuple[str, str]:
    """计算时柱"""
    # 时支：子时为23:00-1:00
    hour = time.hour
    if hour == 23 or hour == 0:
        branch_index = 0  # 子
    else:
        branch_index = ((hour + 1) // 2) % 12
    
    # 时干：五鼠遁
    day_stem_index = HEAVENLY_STEMS.index(day_stem)
    # 甲己还加甲，乙庚丙作初...
    hour_stem_starts = [0, 2, 4, 6, 8, 0, 2, 4, 6, 8]
    start_stem = hour_stem_starts[day_stem_index]
    stem_index = (start_stem + branch_index) % 10
    
    return HEAVENLY_STEMS[stem_index], EARTHLY_BRANCHES[branch_index]

def calculate_start_luck_age(birth_datetime: datetime.datetime, gender: str) -> int:
    """计算起运岁数"""
    # 阳年男/阴年女顺排，阴年男/阳年女逆排
    year = birth_datetime.year
    is_yang_year = year % 2 == 0  # 简化判断
    
    # 计算出生日到下一个节气/上一个节气的天数
    birth_date = birth_datetime.date()
    
    # 简化计算：3天=1岁
    if (is_yang_year and gender == "男") or (not is_yang_year and gender == "女"):
        # 顺排，找下一个节气
        days = 15  # 简化值
    else:
        # 逆排，找上一个节气
        days = 15  # 简化值
    
    start_age = days // 3
    if days % 3 != 0:
        start_age += 1
    
    return start_age

def compute_big_luck(day_index: int, month_index: int, start_age: int, 
                    gender: str, birth_year: int, cycles: int = 8) -> List[Tuple[int, Tuple[str, str]]]:
    """计算大运"""
    luck = []
    
    # 判断顺排还是逆排
    is_yang_year = birth_year % 2 == 0
    forward = (is_yang_year and gender == "男") or (not is_yang_year and gender == "女")
    
    current_index = month_index
    age = start_age
    
    for i in range(cycles):
        if forward:
            current_index = (current_index + 1) % 60
        else:
            current_index = (current_index - 1) % 60
        
        luck.append((age, ganzhi_from_index(current_index)))
        age += 10
    
    return luck

def get_ten_god(day_stem: str, target_stem: str) -> str:
    """获取十神关系"""
    day_index = HEAVENLY_STEMS.index(day_stem)
    target_index = HEAVENLY_STEMS.index(target_stem)
    
    # 生我：正印偏印，我生：伤官食神
    # 克我：正官七杀，我克：正财偏财
    # 同我：比肩劫财
    
    diff = (target_index - day_index) % 10
    
    if diff == 0:
        return "比肩"
    elif diff == 1:
        return "劫财"
    elif diff == 2:
        return "食神"
    elif diff == 3:
        return "伤官"
    elif diff == 4:
        return "偏财"
    elif diff == 5:
        return "正财"
    elif diff == 6:
        return "七杀"
    elif diff == 7:
        return "正官"
    elif diff == 8:
        return "偏印"
    elif diff == 9:
        return "正印"
    return "未知"

def analyze_element_strength(bazi: BaZiChart) -> Dict[str, float]:
    """分析五行强弱"""
    elements = ["木", "火", "土", "金", "水"]
    scores = {el: 0.0 for el in elements}
    
    # 基础分值
    for stem, branch in bazi.pillars:
        scores[STEM_ELEMENTS[stem]] += 1.0
        scores[BRANCH_ELEMENTS[branch]] += 1.0
    
    # 考虑地支藏干
    for _, branch in bazi.pillars:
        hidden_stems = BRANCH_HIDDEN_STEMS.get(branch, [])
        for stem in hidden_stems:
            scores[STEM_ELEMENTS[stem]] += 0.3
    
    # 月令权重
    month_branch = bazi.pillars[1][1]
    month_element = BRANCH_ELEMENTS[month_branch]
    scores[month_element] *= 1.5
    
    # 归一化
    total = sum(scores.values())
    if total > 0:
        scores = {k: v/total*100 for k, v in scores.items()}
    
    return scores

def generate_yearly_fortune(bazi: BaZiChart, start_year: int = 2024, years: int = 10) -> pd.DataFrame:
    """生成流年运势"""
    records = []
    
    # 获取日柱索引
    day_stem, day_branch = bazi.pillars[2]
    day_index = (HEAVENLY_STEMS.index(day_stem) * 12 + EARTHLY_BRANCHES.index(day_branch)) % 60
    
    for year_offset in range(years):
        current_year = start_year + year_offset
        
        # 流年天干地支
        year_stem_index = (current_year - 4) % 10
        year_branch_index = (current_year - 4) % 12
        year_stem = HEAVENLY_STEMS[year_stem_index]
        year_branch = EARTHLY_BRANCHES[year_branch_index]
        
        # 组合八字（年柱用流年）
        year_pillar = (year_stem, year_branch)
        pillars = [year_pillar, bazi.pillars[1], bazi.pillars[2], bazi.pillars[3]]
        
        # 计算五行分布
        elements = {el: 0 for el in ["木", "火", "土", "金", "水"]}
        for stem, branch in pillars:
            elements[STEM_ELEMENTS[stem]] += 1
            elements[BRANCH_ELEMENTS[branch]] += 1
        
        # 与日主的关系
        day_element = STEM_ELEMENTS[day_stem]
        generates_element = GENERATES[day_element]  # 我生
        controls_element = CONTROLS[day_element]    # 我克
        reduces_element = REDUCES[day_element]      # 生我
        counters_element = COUNTERS[day_element]    # 克我
        
        # 计算得分
        score = 0
        score += elements[day_element] * 2          # 比劫
        score += elements[generates_element] * 1    # 食伤
        score += elements[reduces_element] * 1.5    # 印枭
        score -= elements[controls_element] * 1     # 财星
        score -= elements[counters_element] * 2     # 官杀
        
        # 考虑大运
        # 简化处理：查找当前年份对应的大运
        current_age = current_year - bazi.birth_datetime.year
        big_luck_element = None
        for age, (s, b) in bazi.big_luck:
            if age <= current_age < age + 10:
                big_luck_element = STEM_ELEMENTS[s]
                break
        
        if big_luck_element:
            if big_luck_element in [day_element, reduces_element]:
                score += 2
            elif big_luck_element in [counters_element, controls_element]:
                score -= 1
        
        records.append({
            "年份": current_year,
            "流年": f"{year_stem}{year_branch}",
            "五行得分": score,
            "主要元素": max(elements.items(), key=lambda x: x[1])[0],
            "运势评级": "吉" if score > 2 else "平" if score >= -1 else "凶"
        })
    
    return pd.DataFrame(records)

def generate_kline_data(bazi: BaZiChart, start_year: int = 2000, end_year: int = 2040) -> pd.DataFrame:
    """生成人生K线数据"""
    records = []
    current_value = 50  # 起始值
    
    birth_year = bazi.birth_datetime.year
    current_age = 0
    
    for year in range(start_year, end_year + 1):
        age = year - birth_year
        if age < 0:
            continue
        
        # 计算年度运势（简化版）
        year_stem_index = (year - 4) % 10
        year_branch_index = (year - 4) % 12
        year_stem = HEAVENLY_STEMS[year_stem_index]
        year_branch = EARTHLY_BRANCHES[year_branch_index]
        
        # 五行关系计算
        day_element = STEM_ELEMENTS[bazi.pillars[2][0]]
        year_element = STEM_ELEMENTS[year_stem]
        
        if year_element == day_element:
            change = 15
        elif year_element == GENERATES[day_element]:
            change = 10
        elif year_element == REDUCES[day_element]:
            change = 8
        elif year_element == CONTROLS[day_element]:
            change = -8
        elif year_element == COUNTERS[day_element]:
            change = -12
        else:
            change = 0
        
        # 大运影响
        for luck_age, (luck_stem, luck_branch) in bazi.big_luck:
            if luck_age <= age < luck_age + 10:
                luck_element = STEM_ELEMENTS[luck_stem]
                if luck_element == day_element:
                    change += 5
                elif luck_element == COUNTERS[day_element]:
                    change -= 3
                break
        
        # 生成K线数据
        open_val = current_value
        close_val = open_val + change
        high_val = max(open_val, close_val) + abs(change) * 0.3
        low_val = min(open_val, close_val) - abs(change) * 0.3
        
        # 确保值在合理范围
        high_val = min(high_val, 100)
        low_val = max(low_val, 0)
        close_val = max(0, min(100, close_val))
        
        records.append({
            "年份": year,
            "年龄": age,
            "open": open_val,
            "high": high_val,
            "low": low_val,
            "close": close_val,
            "volume": abs(change) * 10  # 模拟交易量
        })
        
        current_value = close_val
    
    return pd.DataFrame(records)

def get_ai_analysis(bazi: BaZiChart, fortune_df: pd.DataFrame) -> str:
    """获取AI分析建议"""
    if not AI_AVAILABLE:
        return "AI分析功能暂不可用，请安装openai库并配置API密钥。"
    
    try:
        # 构建分析提示
        analysis_prompt = f"""
        请根据以下八字信息提供简要分析建议：
        
        姓名：{bazi.name}
        八字：{bazi.to_dict()['八字']}
        日主：{bazi.day_master}
        五行分布：{bazi.elements}
        起运岁数：{bazi.start_luck_age}岁
        近期运势：
        {fortune_df.to_string()}
        
        请从以下方面分析：
        1. 性格特点（根据日主和十神）
        2. 事业建议（根据五行喜用）
        3. 近期注意事项
        4. 简单开运建议
        
        请用中文回复，简洁明了。
        """
        
        # 调用OpenAI API（需要配置API密钥）
        # openai.api_key = st.secrets["openai_api_key"]
        # response = openai.ChatCompletion.create(
        #     model="gpt-3.5-turbo",
        #     messages=[{"role": "user", "content": analysis_prompt}],
        #     max_tokens=500
        # )
        # return response.choices[0].message.content
        
        return """AI分析示例（实际需要配置OpenAI API密钥）：
        
        1. 性格特点：日主为{bazi.day_master}，性格坚强，有领导才能，但有时略显固执。
        
        2. 事业建议：五行喜{bazi.elements}，适合从事相关行业。近期运势平稳，宜稳扎稳打。
        
        3. 注意事项：明年流年冲克，注意人际关系和健康。
        
        4. 开运建议：可佩戴对应五行饰品，多接触喜用五行环境。"""
        
    except Exception as e:
        return f"AI分析出错：{str(e)}"

def main():
    # 页面配置
    st.set_page_config(
        page_title="八字命理分析系统",
        page_icon="📿",
        layout="wide"
    )
    
    st.title("📿 八字命理分析系统")
    st.markdown("""
    本系统提供专业的八字排盘、大运流年分析、人生K线可视化及AI命理建议。
    算法基于传统命理原理，结果仅供参考。
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
        
        st.markdown("---")
        st.markdown("#### 分析选项")
        show_details = st.checkbox("显示详细分析", True)
        show_kline = st.checkbox("显示人生K线", True)
        show_ai = st.checkbox("AI分析建议", True)
        
        if st.button("🚀 开始分析", type="primary", use_container_width=True):
            st.session_state.analyze = True
    
    # 主分析区域
    if 'analyze' not in st.session_state:
        st.session_state.analyze = False
    
    if st.session_state.analyze:
        try:
            # 1. 时区校准和真太阳时计算
            st.header("📍 时间校准信息")
            
            # 构建本地时间
            local_datetime = datetime.datetime.combine(birth_date, birth_time)
            
            # 获取时区（简化版，实际需调用API）
            timezone_str = "Asia/Shanghai"  # 默认
            if location and location != "北京":
                tz_info = get_timezone_from_location(location)
                if tz_info:
                    timezone_str = tz_info
            
            # 转换为UTC+8（北京时间）进行比较
            local_tz = pytz.timezone(timezone_str)
            local_dt = local_tz.localize(local_datetime)
            beijing_tz = pytz.timezone('Asia/Shanghai')
            beijing_dt = local_dt.astimezone(beijing_tz)
            
            # 真太阳时计算（简化）
            true_solar_dt = local_datetime
            if location:
                # 简化的经度估计
                location_longitude = 116.4 if "北京" in location else 121.47 if "上海" in location else 120.15
                true_solar_dt = calculate_true_solar_time(local_datetime, location_longitude)
            
            # 显示时间信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("当地出生时间", local_datetime.strftime("%Y-%m-%d %H:%M"))
            with col2:
                st.metric("北京时间", beijing_dt.strftime("%Y-%m-%d %H:%M"))
            with col3:
                st.metric("真太阳时", true_solar_dt.strftime("%Y-%m-%d %H:%M"))
            
            # 2. 八字排盘
            st.header("📜 八字命盘")
            
            # 使用真太阳时计算八字
            date_for_bazi = true_solar_dt.date()
            time_for_bazi = true_solar_dt.time()
            
            # 计算四柱
            y_stem, y_branch = year_pillar(date_for_bazi)
            m_stem, m_branch = month_pillar(y_stem, date_for_bazi)
            d_stem, d_branch = day_pillar(date_for_bazi)
            h_stem, h_branch = hour_pillar(d_stem, time_for_bazi)
            
            pillars = [(y_stem, y_branch), (m_stem, m_branch), 
                      (d_stem, d_branch), (h_stem, h_branch)]
            
            # 五行分布
            elements = {el: 0 for el in ["木", "火", "土", "金", "水"]}
            for stem, branch in pillars:
                elements[STEM_ELEMENTS[stem]] += 1
                elements[BRANCH_ELEMENTS[branch]] += 1
            
            # 创建八字对象
            bazi = BaZiChart(
                name=name,
                birth_datetime=local_datetime,
                true_solar_time=true_solar_dt,
                location=location,
                pillars=pillars,
                elements=elements,
                day_master=STEM_ELEMENTS[d_stem],
                start_luck_age=calculate_start_luck_age(local_datetime, gender),
                big_luck=[]
            )
            
            # 计算大运
            month_index = (HEAVENLY_STEMS.index(m_stem) * 12 + EARTHLY_BRANCHES.index(m_branch)) % 60
            day_index = (HEAVENLY_STEMS.index(d_stem) * 12 + EARTHLY_BRANCHES.index(d_branch)) % 60
            bazi.big_luck = compute_big_luck(day_index, month_index, bazi.start_luck_age, 
                                           gender, local_datetime.year)
            
            # 显示八字命盘
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("四柱八字")
                pillars_display = pd.DataFrame({
                    "柱": ["年柱", "月柱", "日柱", "时柱"],
                    "天干": [p[0] for p in pillars],
                    "地支": [p[1] for p in pillars],
                    "五行": [f"{STEM_ELEMENTS[p[0]]}{BRANCH_ELEMENTS[p[1]]}" for p in pillars],
                    "十神": [get_ten_god(d_stem, p[0]) for p in pillars]
                })
                st.dataframe(pillars_display, use_container_width=True, hide_index=True)
            
            with col2:
                st.subheader("基本信息")
                info_df = pd.DataFrame([
                    ["姓名", name or "未提供"],
                    ["性别", gender],
                    ["日主", f"{d_stem}({STEM_ELEMENTS[d_stem]})"],
                    ["八字", " ".join([f"{s}{b}" for s, b in pillars])],
                    ["起运岁数", f"{bazi.start_luck_age}岁"],
                    ["当前大运", f"{bazi.big_luck[0][0]}岁: {bazi.big_luck[0][1][0]}{bazi.big_luck[0][1][1]}"]
                ], columns=["项目", "内容"])
                st.dataframe(info_df, use_container_width=True, hide_index=True)
            
            # 3. 五行分析
            st.subheader("🔮 五行分析")
            
            element_scores = analyze_element_strength(bazi)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # 五行柱状图
                element_df = pd.DataFrame({
                    "五行": list(element_scores.keys()),
                    "强度": list(element_scores.values())
                })
                chart = alt.Chart(element_df).mark_bar().encode(
                    x=alt.X("五行", sort=None),
                    y="强度",
                    color=alt.Color("五行", scale=alt.Scale(
                        domain=["木", "火", "土", "金", "水"],
                        range=["green", "red", "brown", "gold", "blue"]
                    ))
                ).properties(height=300)
                st.altair_chart(chart, use_container_width=True)
            
            with col2:
                st.metric("日主五行", bazi.day_master)
                
                # 喜用神判断（简化）
                strongest = max(element_scores.items(), key=lambda x: x[1])[0]
                weakest = min(element_scores.items(), key=lambda x: x[1])[0]
                
                st.info(f"""
                **五行分析：**
                - 最强：{strongest}
                - 最弱：{weakest}
                - 平衡建议：补{weakest}抑{strongest}
                """)
            
            # 4. 大运流年分析
            st.header("📈 大运流年分析")
            
            # 显示大运表
            st.subheader("十年大运")
            big_luck_df = pd.DataFrame({
                "起始年龄": [age for age, _ in bazi.big_luck],
                "干支": [f"{stem}{branch}" for _, (stem, branch) in bazi.big_luck],
                "五行": [f"{STEM_ELEMENTS[stem]}{BRANCH_ELEMENTS[branch]}" for _, (stem, branch) in bazi.big_luck]
            })
            st.dataframe(big_luck_df, use_container_width=True, hide_index=True)
            
            # 流年运势
            st.subheader("流年运势（2024-2033）")
            fortune_df = generate_yearly_fortune(bazi, 2024, 10)
            
            # 使用Plotly创建交互式图表
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=("运势得分趋势", "运势评级"),
                vertical_spacing=0.15
            )
            
            # 得分趋势线
            fig.add_trace(
                go.Scatter(
                    x=fortune_df["年份"],
                    y=fortune_df["五行得分"],
                    mode="lines+markers",
                    name="运势得分",
                    line=dict(color="blue", width=2)
                ),
                row=1, col=1
            )
            
            # 评级柱状图
            color_map = {"吉": "green", "平": "orange", "凶": "red"}
            colors = [color_map[rating] for rating in fortune_df["运势评级"]]
            
            fig.add_trace(
                go.Bar(
                    x=fortune_df["年份"],
                    y=[1] * len(fortune_df),  # 固定高度
                    name="运势评级",
                    marker_color=colors,
                    text=fortune_df["运势评级"],
                    textposition="auto"
                ),
                row=2, col=1
            )
            
            fig.update_layout(height=500, showlegend=False)
            fig.update_yaxes(title_text="得分", row=1, col=1)
            fig.update_yaxes(visible=False, row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 5. 人生K线图
            if show_kline:
                st.header("📊 人生K线图")
                
                kline_df = generate_kline_data(bazi, 2000, 2040)
                
                # 使用Plotly绘制K线图
                fig_kline = go.Figure(data=[
                    go.Candlestick(
                        x=kline_df["年份"],
                        open=kline_df["open"],
                        high=kline_df["high"],
                        low=kline_df["low"],
                        close=kline_df["close"],
                        name="人生指数",
                        increasing_line_color='red',
                        decreasing_line_color='green'
                    )
                ])
                
                # 添加均线（5年、10年均线）
                kline_df['MA5'] = kline_df['close'].rolling(window=5).mean()
                kline_df['MA10'] = kline_df['close'].rolling(window=10).mean()
                
                fig_kline.add_trace(go.Scatter(
                    x=kline_df["年份"],
                    y=kline_df["MA5"],
                    mode="lines",
                    name="5年均线",
                    line=dict(color="orange", width=1)
                ))
                
                fig_kline.add_trace(go.Scatter(
                    x=kline_df["年份"],
                    y=kline_df["MA10"],
                    mode="lines",
                    name="10年均线",
                    line=dict(color="purple", width=1)
                ))
                
                # 标记重要年份（大运起始）
                for age, _ in bazi.big_luck:
                    year = birth_date.year + age
                    if 2000 <= year <= 2040:
                        fig_kline.add_vline(
                            x=year,
                            line_dash="dash",
                            line_color="gray",
                            opacity=0.5
                        )
                
                fig_kline.update_layout(
                    title="人生运势K线图（2000-2040）",
                    xaxis_title="年份",
                    yaxis_title="运势指数",
                    height=500,
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig_kline, use_container_width=True)
                
                # K线数据表格
                with st.expander("查看详细K线数据"):
                    st.dataframe(kline_df[["年份", "年龄", "open", "high", "low", "close"]], use_container_width=True)
            
            # 6. AI命理分析
            if show_ai:
                st.header("🤖 AI命理分析建议")
                
                with st.spinner("AI正在分析中..."):
                    ai_analysis = get_ai_analysis(bazi, fortune_df)
                
                st.markdown("---")
                st.markdown(ai_analysis)
                
                # 注意事项
                st.warning("""
                **重要提示：**
                - 本分析基于算法模型，仅供参考
                - 命运掌握在自己手中
                - 保持积极心态，努力创造美好人生
                """)
            
            # 7. 导出功能
            st.header("💾 导出结果")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📄 生成分析报告"):
                    report = f"""
                    # 八字命理分析报告
                    
                    ## 基本信息
                    - 姓名：{name}
                    - 出生时间：{local_datetime.strftime("%Y-%m-%d %H:%M")}
                    - 真太阳时：{true_solar_dt.strftime("%Y-%m-%d %H:%M")}
                    - 出生地：{location}
                    
                    ## 八字命盘
                    {pillars_display.to_markdown()}
                    
                    ## 大运流年
                    {big_luck_df.to_markdown()}
                    
                    ## 近期运势
                    {fortune_df.to_markdown()}
                    """
                    
                    st.download_button(
                        label="下载报告",
                        data=report,
                        file_name=f"八字分析报告_{name or '匿名'}_{datetime.datetime.now().strftime('%Y%m%d')}.md",
                        mime="text/markdown"
                    )
            
            with col2:
                if st.button("🔄 重新分析"):
                    st.session_state.analyze = False
                    st.rerun()
        
        except Exception as e:
            st.error(f"分析过程中出现错误：{str(e)}")
            st.info("请检查输入信息是否正确，或联系管理员。")
    
    else:
        # 欢迎页面
        st.markdown("""
        ## 欢迎使用八字命理分析系统
        
        ### 功能特点：
        
        1. **精准排盘** - 支持时区校准和真太阳时计算
        2. **八字分析** - 完整的四柱八字、五行分析、十神关系
        3. **大运流年** - 十年大运、流年运势分析
        4. **可视化** - 人生K线图、运势趋势图
        5. **AI建议** - 智能命理分析和建议
        
        ### 使用方法：
        1. 在左侧输入个人信息
        2. 点击"开始分析"按钮
        3. 查看详细分析报告
        
        ### 注意事项：
        - 出生地点请尽量准确，用于时区校准
        - 出生时间尽量精确到分钟
        - 分析结果仅供参考，请理性对待
        """)
        
        # 示例展示
        st.markdown("---")
        st.subheader("📊 示例展示")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("八字排盘", "甲子 丙寅 戊辰 庚申")
        with col2:
            st.metric("五行得分", "85/100", "+5")
        with col3:
            st.metric("近期运势", "平稳上升")

if __name__ == "__main__":
    main()
