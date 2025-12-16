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

import datetime
from dataclasses import dataclass
from typing import List, Tuple, Dict

import pandas as pd
import streamlit as st
import altair as alt


# Constants for Heavenly Stems and Earthly Branches
HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# Mapping of stems and branches to Five Elements
# Wood(木), Fire(火), Earth(土), Metal(金), Water(水)
STEM_ELEMENTS: Dict[str, str] = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火",
    "戊": "土", "己": "土", "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}
BRANCH_ELEMENTS: Dict[str, str] = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}


def ganzhi_from_index(index: int) -> Tuple[str, str]:
    """Given a 0‑based index (0‑59), return the corresponding Heavenly Stem and
    Earthly Branch as a tuple of two strings.
    """
    stem = HEAVENLY_STEMS[index % 10]
    branch = EARTHLY_BRANCHES[index % 12]
    return stem, branch


def year_pillar(date: datetime.date) -> Tuple[str, str]:
    """Compute year Heavenly Stem and Earthly Branch for a Gregorian date.
    This approximation uses the solar (Gregorian) year instead of the lunar
    year.  Chinese astrology traditionally uses the lunar year starting at
    立春 (around 2/4), but for demonstration we ignore that offset.
    """
    stem_index = (date.year - 4) % 10
    branch_index = (date.year - 4) % 12
    return HEAVENLY_STEMS[stem_index], EARTHLY_BRANCHES[branch_index]


def month_pillar(year_stem: str, date: datetime.date) -> Tuple[str, str]:
    """Compute month Heavenly Stem and Earthly Branch.
    The Earthly Branch for months starts with 寅 (Tiger) for the first
    lunar month.  We approximate by mapping January to 寅, February to 卯,
    ..., December to 丑.
    The Heavenly Stem of the month is calculated from the year stem:
    stem_index = (year_stem_index * 2 + month) mod 10.
    """
    # Gregorian month 1 maps to lunar month 3rd branch (寅) -> index 2
    branch_index = (date.month + 1) % 12
    # Determine index of the year's heavenly stem
    stem_index_year = HEAVENLY_STEMS.index(year_stem)
    # Month stem index calculation: (year stem index * 2 + lunar month index) mod 10
    stem_index = (stem_index_year * 2 + date.month) % 10
    return HEAVENLY_STEMS[stem_index], EARTHLY_BRANCHES[branch_index]


def day_pillar(date: datetime.date) -> Tuple[str, str]:
    """Compute day Heavenly Stem and Earthly Branch.
    We take 1900‑01‑01 (Gregorian) as 甲戌日 (sequence index 10 with 0‑based
    indexing).  The index is computed by counting days difference and
    applying modulo 60.  This base is derived from scholarly references
    on Chinese calendar calculations【915535503091376†L41-L60】.
    """
    base_date = datetime.date(1900, 1, 1)
    base_index = 10  # 甲戌 corresponds to sequence number 11 (1‑based), so index 10
    delta_days = (date - base_date).days
    index = (base_index + delta_days) % 60
    return ganzhi_from_index(index)


def hour_pillar(day_stem: str, time: datetime.time) -> Tuple[str, str]:
    """Compute hour Heavenly Stem and Earthly Branch.
    Earthly Branches for hours: each branch corresponds to a two‑hour
    period starting at 23:00 (子时).  The Heavenly Stem is
    (day_stem_index * 2 + hour_branch_index) mod 10.
    """
    # Determine branch index: 23:00–00:59 -> 0, 01:00–02:59 -> 1, etc.
    total_minutes = time.hour * 60 + time.minute
    # Starting at 23:00 = -60 minutes; adjust into 0–23 hours range
    hours_from_zi = ((time.hour + 1) % 24) // 2
    branch_index = hours_from_zi % 12
    # Heavenly stem index for hour
    day_stem_index = HEAVENLY_STEMS.index(day_stem)
    stem_index = (day_stem_index * 2 + branch_index) % 10
    return HEAVENLY_STEMS[stem_index], EARTHLY_BRANCHES[branch_index]


def five_element_distribution(pillars: List[Tuple[str, str]]) -> Dict[str, int]:
    """Count occurrences of five elements among a list of (stem, branch) tuples.
    """
    counts = {element: 0 for element in ["木", "火", "土", "金", "水"]}
    for stem, branch in pillars:
        counts[STEM_ELEMENTS[stem]] += 1
        counts[BRANCH_ELEMENTS[branch]] += 1
    return counts


def compute_big_luck(day_index: int, month_index: int, start_age: int = 0,
                     cycles: int = 8) -> List[Tuple[int, Tuple[str, str]]]:
    """Compute a list of big luck cycles starting from a given age.

    In traditional BaZi, the first ten‑year luck cycle starts sometime
    between birth and ten years old.  Here we simply start at 10‑year
    intervals from start_age.  Each cycle uses the next Heavenly Stem
    and Earthly Branch in the sexagenary sequence.
    """
    luck = []
    # Starting index for first luck cycle: one step after month pillar
    current_index = (month_index + 1) % 60
    age = start_age
    for i in range(cycles):
        luck.append((age, ganzhi_from_index(current_index)))
        current_index = (current_index + 1) % 60
        age += 10
    return luck


def compute_fortune_index(luck: List[Tuple[int, Tuple[str, str]]], day_element: str) -> pd.DataFrame:
    """Given the big luck list and the day master element, compute a simple
    fortune index for each cycle and convert to a candlestick style DataFrame.

    Favourable elements are defined as the day element itself and the
    element that generates it (e.g. Wood -> Water & Wood, Fire -> Wood & Fire,
    Earth -> Fire & Earth, Metal -> Earth & Metal, Water -> Metal & Water).
    Unfavourable elements are the element that controls the day element and
    the element that is controlled by it.  The index is computed as
    favourable_count - unfavourable_count.
    The candlestick data uses the previous index as 'open' and the
    current index as 'close', with high/low at max/min.
    """
    # Define generating and controlling relationships
    generates = {
        "木": "火", "火": "土", "土": "金", "金": "水", "水": "木"
    }
    controls = {
        "木": "土", "土": "水", "水": "火", "火": "金", "金": "木"
    }
    favourable = {day_element, generates[day_element]}
    unfavourable = {controls[day_element], generates[controls[day_element]]}
    # Build DataFrame
    records = []
    prev_index = 0
    for age, (stem, branch) in luck:
        # Determine elements for this luck pillar
        elements = [STEM_ELEMENTS[stem], BRANCH_ELEMENTS[branch]]
        fav_count = sum(1 for el in elements if el in favourable)
        unfav_count = sum(1 for el in elements if el in unfavourable)
        value = fav_count - unfav_count
        open_val = prev_index
        close_val = open_val + value
        high_val = max(open_val, close_val)
        low_val = min(open_val, close_val)
        records.append({"age": age,
                        "open": open_val,
                        "high": high_val,
                        "low": low_val,
                        "close": close_val})
        prev_index = close_val
    df = pd.DataFrame(records)
    return df


def main() -> None:
    st.title("八字命运可视化 Demo")
    st.markdown(
        "本应用演示如何根据出生日期和时间生成简易的四柱八字，并依据五行强弱推算十年大运走势，"
        "以金融K线的形式展示人生起落。算法为示例用途，并非专业命理预测。"
    )

    # Input widgets
    name = st.text_input("姓名（可选）", "")
    col1, col2 = st.columns(2)
    birth_date = col1.date_input("出生日期", datetime.date(1990, 1, 1))
    birth_time = col2.time_input("出生时间", datetime.time(0, 0))
    tz_offset = st.slider("出生地与东八区时差（小时）", -12, 12, 0)

    if st.button("生成命盘和K线"):
        # Adjust time by timezone offset relative to Beijing (UTC+8)
        adjusted_datetime = datetime.datetime.combine(birth_date, birth_time) + datetime.timedelta(hours=-tz_offset)
        date = adjusted_datetime.date()
        time = adjusted_datetime.time()

        # Calculate pillars
        y_stem, y_branch = year_pillar(date)
        m_stem, m_branch = month_pillar(y_stem, date)
        d_stem, d_branch = day_pillar(date)
        h_stem, h_branch = hour_pillar(d_stem, time)

        pillars = [(y_stem, y_branch), (m_stem, m_branch), (d_stem, d_branch), (h_stem, h_branch)]

        st.subheader("四柱八字")
        df_pillars = pd.DataFrame(
            {
                "柱": ["年柱", "月柱", "日柱", "时柱"],
                "天干": [p[0] for p in pillars],
                "地支": [p[1] for p in pillars],
            }
        )
        st.table(df_pillars)

        # Five element distribution
        counts = five_element_distribution(pillars)
        st.subheader("五行分布")
        st.bar_chart(pd.DataFrame.from_dict(counts, orient="index", columns=["数量"]))

        # Big luck cycles
        # Compute indices for month pillar and day pillar for cycle start
        # Convert month and day pillars back to sexagenary indices
        month_index = (HEAVENLY_STEMS.index(m_stem) * 12 + EARTHLY_BRANCHES.index(m_branch)) % 60
        day_index = (HEAVENLY_STEMS.index(d_stem) * 12 + EARTHLY_BRANCHES.index(d_branch)) % 60
        luck_list = compute_big_luck(day_index, month_index, start_age=0, cycles=8)
        st.subheader("十年大运")
        luck_df = pd.DataFrame(
            {
                "年龄": [age for age, _ in luck_list],
                "大运": [stem + branch for _, (stem, branch) in luck_list],
            }
        )
        st.table(luck_df)

        # Fortune index and K-line
        day_element = STEM_ELEMENTS[d_stem]
        kline_df = compute_fortune_index(luck_list, day_element)
        st.subheader("人生K线 (示例)")
        base = alt.Chart(kline_df).encode(x='age:O')
        rule = base.mark_rule().encode(y='low:Q', y2='high:Q')
        bar = base.mark_bar().encode(y='open:Q', y2='close:Q', color=alt.condition("close>open", alt.value("#EF5350"), alt.value("#26A69A")))
        chart = (rule + bar).properties(width=600, height=400)
        st.altair_chart(chart, use_container_width=True)

        st.markdown(
            "**提示：** 本K线图以五行中有利/不利元素的数量差异作为指数，"
            "不代表真实的命理预测，仅供探索命理可视化思路使用。"
        )


if __name__ == "__main__":
    main()