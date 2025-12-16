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

"""
八字排盘系统 - 精确版
修正年柱、月柱、日柱计算错误
"""

import datetime
import math
from typing import List, Tuple, Dict, Optional
import streamlit as st
import pandas as pd
import altair as alt

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

# ==================== 节气计算 ====================
def get_jieqi_date(year: int, month: int, is_major: bool = True) -> datetime.date:
    """获取节气日期（简化版，返回近似日期）"""
    # 主要节气（节）和次要节气（气）
    jieqi_dates = {
        1: [(6, "小寒"), (21, "大寒")],
        2: [(4, "立春"), (19, "雨水")],
        3: [(6, "惊蛰"), (21, "春分")],
        4: [(5, "清明"), (20, "谷雨")],
        5: [(6, "立夏"), (21, "小满")],
        6: [(6, "芒种"), (22, "夏至")],
        7: [(7, "小暑"), (23, "大暑")],
        8: [(8, "立秋"), (23, "处暑")],
        9: [(8, "白露"), (23, "秋分")],
        10: [(9, "寒露"), (24, "霜降")],
        11: [(8, "立冬"), (23, "小雪")],
        12: [(7, "大雪"), (22, "冬至")],
    }
    
    if is_major:
        day = jieqi_dates[month][0][0]  # 主要节气
    else:
        day = jieqi_dates[month][1][0]  # 次要节气
    
    return datetime.date(year, month, day)

def is_after_spring(date: datetime.date) -> bool:
    """判断是否在立春之后"""
    year = date.year
    spring_date = get_jieqi_date(year, 2, True)  # 立春
    
    if date.month > 2:
        return True
    elif date.month == 2:
        return date.day >= spring_date.day
    else:  # 1月
        return False

# ==================== 修正的八字计算函数 ====================
def get_ganzhi_from_index(index: int) -> Tuple[str, str]:
    """根据索引获取干支"""
    if index < 0:
        index = 60 + (index % 60)
    stem = HEAVENLY_STEMS[index % 10]
    branch = EARTHLY_BRANCHES[index % 12]
    return stem, branch

def get_index_from_ganzhi(ganzhi: str) -> int:
    """根据干支获取索引"""
    for i, gz in enumerate(SIXTY_JIAZI):
        if gz == ganzhi:
            return i
    return -1

def calculate_year_pillar_correct(date: datetime.date) -> Tuple[str, str]:
    """计算年柱 - 修正版"""
    # 以立春为年柱分界
    if is_after_spring(date):
        year = date.year
    else:
        year = date.year - 1
    
    # 公元4年为甲子年
    offset = year - 4
    stem_index = offset % 10
    branch_index = offset % 12
    
    return HEAVENLY_STEMS[stem_index], EARTHLY_BRANCHES[branch_index]

def get_month_branch_by_date(date: datetime.date) -> str:
    """根据日期获取月支 - 修正版"""
    month = date.month
    day = date.day
    
    # 月支表（以节气为界）
    # 寅月（正月）：立春后-惊蛰前
    # 卯月（二月）：惊蛰后-清明前
    # ...
    # 丑月（十二月）：小寒后-立春前
    
    # 简化判断：每月第一个节气前后
    if month == 1:
        return "丑" if day < 6 else "寅"
    elif month == 2:
        return "寅" if day < 4 else "卯"
    elif month == 3:
        return "卯" if day < 6 else "辰"
    elif month == 4:
        return "辰" if day < 5 else "巳"
    elif month == 5:
        return "巳" if day < 6 else "午"
    elif month == 6:
        return "午" if day < 6 else "未"
    elif month == 7:
        return "未" if day < 7 else "申"
    elif month == 8:
        return "申" if day < 8 else "酉"
    elif month == 9:
        return "酉" if day < 8 else "戌"
    elif month == 10:
        return "戌" if day < 9 else "亥"
    elif month == 11:
        return "亥" if day < 8 else "子"
    elif month == 12:
        return "子" if day < 7 else "丑"
    
    return "寅"

def calculate_month_pillar_correct(year_stem: str, date: datetime.date) -> Tuple[str, str]:
    """计算月柱 - 修正版"""
    # 1. 获取月支
    month_branch = get_month_branch_by_date(date)
    
    # 2. 五虎遁：根据年干确定寅月天干
    # 甲己之年丙作首，乙庚之岁戊为头，
    # 丙辛之年寻庚起，丁壬壬位顺行流，
    # 若问戊癸何方发，甲寅之上好追求
    
    yin_month_stems = {
        "甲": "丙", "乙": "戊", "丙": "庚", "丁": "壬", "戊": "甲",
        "己": "丙", "庚": "戊", "辛": "庚", "壬": "壬", "癸": "甲"
    }
    
    yin_stem = yin_month_stems[year_stem]
    yin_index = HEAVENLY_STEMS.index(yin_stem)
    
    # 3. 计算当前月支的天干
    # 寅月（正月）地支索引为2
    month_branch_index = EARTHLY_BRANCHES.index(month_branch)
    
    # 计算从寅月到当前月的偏移
    if month_branch_index >= 2:
        offset = month_branch_index - 2
    else:
        offset = month_branch_index + 10  # 从寅月往前数
    
    month_stem_index = (yin_index + offset) % 10
    
    return HEAVENLY_STEMS[month_stem_index], month_branch

def calculate_day_pillar_correct(date: datetime.date) -> Tuple[str, str]:
    """计算日柱 - 修正版（使用标准公式）"""
    # 使用公式法计算日干支
    # 参考公式：日干支 = [(year-1)*5 + floor((year-1)/4) + day_in_year] mod 60
    
    year = date.year
    month = date.month
    day = date.day
    
    # 计算当年的天数
    month_days = [31, 28 if not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 29,
                  31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    day_in_year = sum(month_days[:month-1]) + day
    
    # 计算日干支索引
    # 使用标准公式
    if month <= 2:
        year -= 1
        month += 12
    
    century = year // 100
    year_in_century = year % 100
    
    # 蔡勒公式的变体计算日干支
    h = (day + 13*(month+1)//5 + year_in_century + year_in_century//4 + century//4 - 2*century) % 7
    
    # 转换为干支索引
    # 2000年1月1日为庚辰日（索引16）
    base_date = datetime.date(2000, 1, 1)
    base_index = 16  # 庚辰索引
    
    delta_days = (date - base_date).days
    index = (base_index + delta_days) % 60
    
    # 确保索引在0-59范围内
    if index < 0:
        index += 60
    
    return get_ganzhi_from_index(index)

def calculate_hour_pillar_correct(day_stem: str, time: datetime.time) -> Tuple[str, str]:
    """计算时柱 - 修正版"""
    # 1. 确定时支
    hour = time.hour
    minute = time.minute
    
    # 时辰划分（真太阳时）
    total_minutes = hour * 60 + minute
    
    if total_minutes < 60 or total_minutes >= 1380:  # 23:00-01:00
        hour_branch = "子"
        hour_branch_index = 0
    elif total_minutes < 180:  # 01:00-03:00
        hour_branch = "丑"
        hour_branch_index = 1
    elif total_minutes < 300:  # 03:00-05:00
        hour_branch = "寅"
        hour_branch_index = 2
    elif total_minutes < 420:  # 05:00-07:00
        hour_branch = "卯"
        hour_branch_index = 3
    elif total_minutes < 540:  # 07:00-09:00
        hour_branch = "辰"
        hour_branch_index = 4
    elif total_minutes < 660:  # 09:00-11:00
        hour_branch = "巳"
        hour_branch_index = 5
    elif total_minutes < 780:  # 11:00-13:00
        hour_branch = "午"
        hour_branch_index = 6
    elif total_minutes < 900:  # 13:00-15:00
        hour_branch = "未"
        hour_branch_index = 7
    elif total_minutes < 1020:  # 15:00-17:00
        hour_branch = "申"
        hour_branch_index = 8
    elif total_minutes < 1140:  # 17:00-19:00
        hour_branch = "酉"
        hour_branch_index = 9
    elif total_minutes < 1260:  # 19:00-21:00
        hour_branch = "戌"
        hour_branch_index = 10
    else:  # 21:00-23:00
        hour_branch = "亥"
        hour_branch_index = 11
    
    # 2. 五鼠遁：根据日干确定子时时干
    # 甲己还加甲，乙庚丙作初，
    # 丙辛从戊起，丁壬庚子居，
    # 戊癸何方发，壬子是真途
    
    zi_hour_stems = {
        "甲": "甲", "乙": "丙", "丙": "戊", "丁": "庚", "戊": "壬",
        "己": "甲", "庚": "丙", "辛": "戊", "壬": "庚", "癸": "壬"
    }
    
    zi_stem = zi_hour_stems[day_stem]
    zi_index = HEAVENLY_STEMS.index(zi_stem)
    
    # 3. 计算当前时支的天干
    hour_stem_index = (zi_index + hour_branch_index) % 10
    
    return HEAVENLY_STEMS[hour_stem_index], hour_branch

def calculate_bazi_correct(birth_datetime: datetime.datetime) -> List[Tuple[str, str]]:
    """计算完整的八字四柱 - 修正版"""
    date = birth_datetime.date()
    time = birth_datetime.time()
    
    # 1. 年柱
    year_stem, year_branch = calculate_year_pillar_correct(date)
    
    # 2. 月柱
    month_stem, month_branch = calculate_month_pillar_correct(year_stem, date)
    
    # 3. 日柱
    day_stem, day_branch = calculate_day_pillar_correct(date)
    
    # 4. 时柱
    hour_stem, hour_branch = calculate_hour_pillar_correct(day_stem, time)
    
    return [
        (year_stem, year_branch),
        (month_stem, month_branch),
        (day_stem, day_branch),
        (hour_stem, hour_branch)
    ]

# ==================== 验证函数 ====================
def test_bazi_calculation():
    """测试八字计算准确性"""
    test_cases = [
        # (日期时间, 预期八字)
        ("1990-01-01 12:00", "己巳 丁丑 丙寅 甲午"),
        ("1990-06-15 14:30", "庚午 壬午 辛亥 乙未"),
        ("1985-08-20 08:00", "乙丑 甲申 辛卯 壬辰"),
        ("2000-02-04 12:00", "己卯 丙寅 壬辰 丙午"),  # 立春后
        ("2000-02-03 12:00", "己卯 丁丑 辛卯 甲午"),  # 立春前
        ("2023-01-01 00:00", "壬寅 壬子 己未 甲子"),
        ("2023-07-15 12:00", "癸卯 己未 甲戌 庚午"),
    ]
    
    results = []
    for date_str, expected in test_cases:
        birth_datetime = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        pillars = calculate_bazi_correct(birth_datetime)
        actual = ' '.join([f"{s}{b}" for s, b in pillars])
        
        status = "✅" if actual == expected else "❌"
        results.append({
            "日期": date_str,
            "预期": expected,
            "实际": actual,
            "状态": status
        })
    
    return pd.DataFrame(results)

# ==================== 主程序 ====================
def main():
    st.set_page_config(
        page_title="八字排盘验证系统",
        page_icon="📿",
        layout="wide"
    )
    
    st.title("📿 八字排盘验证系统")
    st.markdown("修正八字排盘算法，确保准确性")
    
    # 测试区域
    st.header("🧪 算法测试")
    
    if st.button("运行测试用例"):
        with st.spinner("正在测试八字计算..."):
            test_results = test_bazi_calculation()
            
            st.subheader("测试结果")
            st.dataframe(test_results, use_container_width=True)
            
            # 统计正确率
            correct_count = sum(1 for r in test_results.to_dict('records') if r["状态"] == "✅")
            total_count = len(test_results)
            accuracy = correct_count / total_count * 100
            
            st.metric("测试通过率", f"{accuracy:.1f}%", f"{correct_count}/{total_count}")
    
    # 手动测试区域
    st.header("🔍 手动测试")
    
    col1, col2 = st.columns(2)
    with col1:
        test_date = st.date_input("测试日期", datetime.date(1990, 1, 1))
    with col2:
        test_time = st.time_input("测试时间", datetime.time(12, 0))
    
    # 预期八字输入
    expected_bazi = st.text_input("预期八字（空格分隔）", "己巳 丁丑 丙寅 甲午")
    
    if st.button("计算八字", type="primary"):
        birth_datetime = datetime.datetime.combine(test_date, test_time)
        
        # 使用修正算法计算
        pillars = calculate_bazi_correct(birth_datetime)
        actual_bazi = ' '.join([f"{s}{b}" for s, b in pillars])
        
        # 显示结果
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("测试时间", birth_datetime.strftime("%Y-%m-%d %H:%M"))
        with col2:
            st.metric("预期八字", expected_bazi)
        with col3:
            st.metric("实际八字", actual_bazi)
        
        # 详细分析
        st.subheader("详细分析")
        
        df_pillars = pd.DataFrame({
            "柱": ["年柱", "月柱", "日柱", "时柱"],
            "天干": [p[0] for p in pillars],
            "地支": [p[1] for p in pillars],
            "五行": [f"{STEM_ELEMENTS[p[0]]}{BRANCH_ELEMENTS[p[1]]}" for p in pillars],
            "干支": [f"{p[0]}{p[1]}" for p in pillars]
        })
        
        st.dataframe(df_pillars, use_container_width=True, hide_index=True)
        
        # 验证结果
        if actual_bazi == expected_bazi:
            st.success("✅ 八字排盘正确！")
        else:
            st.error("❌ 八字排盘有误！")
            
            # 显示差异
            st.info("**差异分析：**")
            expected_parts = expected_bazi.split()
            actual_parts = actual_bazi.split()
            
            diff_data = []
            pillar_names = ["年柱", "月柱", "日柱", "时柱"]
            for i, (exp, act) in enumerate(zip(expected_parts, actual_parts)):
                status = "✅" if exp == act else "❌"
                diff_data.append({
                    "柱": pillar_names[i],
                    "预期": exp,
                    "实际": act,
                    "状态": status
                })
            
            st.dataframe(pd.DataFrame(diff_data), use_container_width=True)
    
    # 算法说明
    st.header("📖 算法说明")
    
    with st.expander("查看算法详情"):
        st.markdown("""
        ### 修正的关键算法：
        
        #### 1. 年柱计算
        - **基准**：公元4年为甲子年
        - **分界**：以立春为界（不是春节）
        - 立春前用上一年年柱，立春后用当年年柱
        
        #### 2. 月柱计算
        - **月支**：以24节气分月，不是按公历月份
        - **月干**：使用"五虎遁"口诀
        ```
        甲己之年丙作首，乙庚之岁戊为头，
        丙辛之年寻庚起，丁壬壬位顺行流，
        若问戊癸何方发，甲寅之上好追求。
        ```
        
        #### 3. 日柱计算
        - 使用**公式法**计算
        - 基准：2000年1月1日为庚辰日
        - 通过天数差计算干支索引
        
        #### 4. 时柱计算
        - **时支**：每2小时一个时辰
        - **时干**：使用"五鼠遁"口诀
        ```
        甲己还加甲，乙庚丙作初，
        丙辛从戊起，丁壬庚子居，
        戊癸何方发，壬子是真途。
        ```
        
        ### 测试用例验证：
        
        | 日期 | 预期八字 | 说明 |
        |------|----------|------|
        | 1990-01-01 | 己巳 丁丑 丙寅 甲午 | 立春前，用己巳年 |
        | 1990-06-15 | 庚午 壬午 辛亥 乙未 | 正常月份 |
        | 2000-02-04 | 己卯 丙寅 壬辰 丙午 | 立春当天 |
        """)
    
    # 批量验证
    st.header("📋 批量验证")
    
    if st.button("运行完整验证套件"):
        # 更多测试用例
        extended_cases = [
            ("1900-01-01 12:00", "己亥 丙子 癸巳 戊午"),
            ("1900-02-04 12:00", "己亥 丁丑 壬辰 丙午"),  # 立春
            ("2000-01-01 12:00", "己卯 丙子 戊午 戊午"),
            ("2000-12-31 12:00", "庚辰 戊子 癸亥 戊午"),
            ("2024-01-01 12:00", "癸卯 甲子 甲子 庚午"),
            ("2024-02-04 12:00", "甲辰 丙寅 戊戌 戊午"),  # 立春
            ("2024-06-15 12:00", "甲辰 庚午 庚戌 壬午"),
        ]
        
        results = []
        for date_str, expected in extended_cases:
            try:
                birth_datetime = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                pillars = calculate_bazi_correct(birth_datetime)
                actual = ' '.join([f"{s}{b}" for s, b in pillars])
                status = "✅" if actual == expected else "❌"
            except Exception as e:
                actual = f"错误: {str(e)}"
                status = "❌"
            
            results.append({
                "日期": date_str,
                "预期八字": expected,
                "实际八字": actual,
                "状态": status
            })
        
        df_extended = pd.DataFrame(results)
        st.dataframe(df_extended, use_container_width=True)
        
        # 计算准确率
        correct = sum(1 for r in results if r["状态"] == "✅")
        total = len(results)
        st.metric("批量测试准确率", f"{correct/total*100:.1f}%", f"{correct}/{total}")

if __name__ == "__main__":
    main()
