"""
股票财报发布后股价波动分析工具
==============================

功能说明：
- 自动获取指定股票的历史财报发布日期
- 分析财报发布日及后续几个交易日的股价表现
- 计算涨跌幅、最大涨跌幅等关键指标
- 输出统计摘要并保存分析结果到CSV文件

使用方法：
- 修改 main 函数中的 stock_name 变量为目标股票代码
- 运行脚本即可生成分析报告

输出文件：
- {股票代码}_earnings_analysis.csv：详细的财报分析数据
"""

import yfinance as yf  # Yahoo Finance API，用于获取股票行情数据
import pandas as pd    # 数据处理库，用于表格操作和计算
from datetime import datetime, timedelta  # 日期时间处理
import numpy as np     # 数值计算库

from curl_cffi import requests  # 用于模拟浏览器请求，绕过反爬检测

import os

# ==================== 代理配置 ====================
# 设置HTTP代理，用于访问Yahoo Finance（如果网络需要代理）
proxy = 'http://30.172.114.63:5782'
os.environ['HTTP_PROXY'] = proxy
os.environ['HTTPS_PROXY'] = proxy

def get_stock_earnings_dates(stock_name):
    """
    获取股票财报发布日期

    功能：
        通过 Yahoo Finance API 获取指定股票的历史财报发布日期

    参数：
        stock_name (str): 股票代码，例如 "MSFT"、"AAPL"、"APP"

    返回：
        list: 财报日期列表，按时间倒序排列（最新的在前）

    技术要点：
        - 使用 curl_cffi 模拟 Chrome 浏览器请求，绕过反爬检测
        - 处理时区问题，将带时区的日期转换为不带时区的日期
        - 如果 API 获取失败，返回预设的手动日期作为备用方案
    """
    # 创建模拟 Chrome 浏览器的会话，避免被反爬机制拦截
    session = requests.Session(impersonate="chrome")
    stock = yf.Ticker(stock_name, session=session)

    # 获取财报日历（DataFrame 格式，包含财报日期和相关信息）
    earnings_dates = stock.earnings_dates

    if earnings_dates is not None and not earnings_dates.empty:
        # 按日期降序排序（最新的财报在前面）
        earnings_dates = earnings_dates.sort_index(ascending=False)
        # 处理夏令时歧义问题：
        # Yahoo Finance 返回的日期可能带有时区信息，这里统一转换为不带时区的日期
        # 避免 pandas 在处理时区时出现 AmbiguousTimeError
        return [date.tz_localize(None) if hasattr(date, 'tz_localize') else date for date in earnings_dates.index.tolist()]
    else:
        print("无法自动获取财报日期，使用手动指定的日期")
        # 备用方案：手动指定的财报日期（需要根据实际股票更新）
        # 注意：这里的日期是微软(MSFT)的财报日期示例，分析其他股票时需要修改
        return [
            datetime(2024, 10, 30),  # Q1 FY2025
            datetime(2024, 7, 30),  # Q4 FY2024
            datetime(2024, 4, 25),  # Q3 FY2024
            datetime(2024, 1, 30),  # Q2 FY2024
            datetime(2023, 10, 24),  # Q1 FY2024
            datetime(2023, 7, 25),  # Q4 FY2023
        ]


def calculate_price_movement(stock_data, earnings_date, days_after=5):
    """
    计算财报发布后的股价波动

    功能：
        分析单个财报发布日期前后的股价表现，计算涨跌幅等关键指标

    参数：
        stock_data (DataFrame): 股票历史数据，包含 Open、High、Low、Close、Volume 等列
        earnings_date (datetime): 财报发布日期
        days_after (int): 计算财报发布后几个交易日的表现，默认5天

    返回：
        dict: 包含以下指标的字典
            - 财报日期: 原始财报发布日期
            - 实际交易日: 实际对应的最接近交易日
            - 财报前收盘价: 财报发布前一个交易日的收盘价
            - 财报日收盘价: 财报发布当天的收盘价
            - 财报日涨跌幅(%): 财报日相对于前一日的涨跌幅
            - 第N日后涨跌幅(%): 第N个交易日后的累计涨跌幅
            - 期间最高价/最低价: 分析期间内的最高/最低价格
            - 最大涨幅(%)/最大跌幅(%): 相对于财报前收盘价的最大涨跌幅

    核心逻辑：
        1. 统一日期格式，处理时区问题
        2. 找到财报发布日对应的最接近交易日
        3. 获取财报前一个交易日的收盘价作为基准价
        4. 计算财报日及后续交易日的涨跌幅
        5. 计算期间内的最大涨跌幅
    """
    try:
        # ==================== 第一步：日期格式统一处理 ====================
        # 确保日期格式一致，并处理时区问题
        # pandas 的 tz_localize(None) 可以移除时区信息
        if hasattr(earnings_date, 'tz_localize'):
            earnings_date = earnings_date.tz_localize(None)
        # normalize() 将时间归一化到当天 00:00:00
        earnings_date = pd.Timestamp(earnings_date).normalize()

        # 确保 stock_data 的索引也没有时区信息
        if stock_data.index.tz is not None:
            stock_data.index = stock_data.index.tz_localize(None)

        # ==================== 第二步：找到财报发布日对应的交易日 ====================
        # 由于财报可能在非交易日发布（或数据源日期不完全匹配），
        # 需要在财报日前后5天内查找实际交易日
        date_range = pd.date_range(
            start=earnings_date - timedelta(days=5),
            end=earnings_date + timedelta(days=1)
        )

        # 获取股票数据中与日期范围有交集的日期
        available_dates = stock_data.index.intersection(date_range)
        if len(available_dates) == 0:
            return None

        # 取最接近财报日的交易日作为"财报日"
        earnings_day = available_dates[-1]

        # ==================== 第三步：获取财报前后的交易日 ====================
        # 获取财报前一个交易日的收盘价（作为计算涨跌幅的基准价）
        pre_dates = stock_data.index[stock_data.index < earnings_day]
        if len(pre_dates) == 0:
            return None
        pre_earnings_day = pre_dates[-1]

        # 获取财报后的交易日列表（用于计算后续表现）
        post_dates = stock_data.index[stock_data.index > earnings_day]

        if len(post_dates) == 0:
            return None

        # ==================== 第四步：提取关键价格数据 ====================
        pre_close = stock_data.loc[pre_earnings_day, 'Close']  # 基准价格
        earnings_day_close = stock_data.loc[earnings_day, 'Close']  # 财报日收盘价

        # ==================== 第五步：计算基础波动指标 ====================
        result = {
            '财报日期': earnings_date.strftime('%Y-%m-%d'),
            '实际交易日': earnings_day.strftime('%Y-%m-%d'),
            '财报前收盘价': round(pre_close, 2),
            '财报日收盘价': round(earnings_day_close, 2),
            # 涨跌幅 = (当日收盘 - 前一日收盘) / 前一日收盘 * 100
            '财报日涨跌幅(%)': round((earnings_day_close - pre_close) / pre_close * 100, 2),
        }

        # ==================== 第六步：计算后续交易日的累计涨跌幅 ====================
        # 遍历财报后的每个交易日，计算累计涨跌幅
        for day in range(1, min(days_after + 1, len(post_dates) + 1)):
            if day <= len(post_dates):
                future_day = post_dates[day - 1]
                future_close = stock_data.loc[future_day, 'Close']

                # 相对于财报前一日的累计涨跌幅
                change_pct = round((future_close - pre_close) / pre_close * 100, 2)
                result[f'第{day}日后涨跌幅(%)'] = change_pct

                # 记录第1个交易日的收盘价
                if day == 1:
                    result[f'第{day}日后收盘价'] = round(future_close, 2)

        # ==================== 第七步：计算期间最大涨跌幅 ====================
        # 在财报日到第N日之间，找出最高价和最低价
        # 这对于判断是否应该设置止盈/止损点很有参考价值
        if len(post_dates) >= days_after:
            period_data = stock_data.loc[
                earnings_day:post_dates[days_after - 1]
            ]
            max_price = period_data['High'].max()  # 期间最高价
            min_price = period_data['Low'].min()   # 期间最低价

            result['期间最高价'] = round(max_price, 2)
            result['期间最低价'] = round(min_price, 2)
            # 最大涨幅：期间最高价相对于基准价
            result['最大涨幅(%)'] = round((max_price - pre_close) / pre_close * 100, 2)
            # 最大跌幅：期间最低价相对于基准价（注意这里可能为负数）
            result['最大跌幅(%)'] = round((min_price - pre_close) / pre_close * 100, 2)

        return result

    except Exception as e:
        print(f"处理 {earnings_date} 时出错: {e}")
        return None


def analyze_stock_earnings(stock_name):
    """
    主函数：分析股票财报发布后的股价波动

    功能：
        执行完整的财报影响分析流程，包括：
        1. 获取股票历史数据
        2. 获取财报日期列表
        3. 计算每次财报后的股价表现
        4. 输出统计摘要
        5. 保存分析结果到CSV文件

    参数：
        stock_name (str): 股票代码，例如 "MSFT"、"AAPL"、"APP"

    返回：
        DataFrame: 包含所有财报分析结果的表格，若失败则返回 None

    输出示例：
        - 控制台输出详细的分析表格和统计摘要
        - CSV文件保存为 {股票代码}_earnings_analysis.csv
    """
    # ==================== 第一步：获取股票历史数据 ====================
    print(f"正在获取 {stock_name} 股票数据...")
    stock = yf.Ticker(stock_name)
    # 获取最近3年的历史数据，包含开盘价、最高价、最低价、收盘价、成交量等
    stock_data = stock.history(period="3y")

    if stock_data.empty:
        print("无法获取股票数据")
        return

    # 统一移除时区信息，避免后续日期比较时出现夏令时问题
    if stock_data.index.tz is not None:
        stock_data.index = stock_data.index.tz_localize(None)

    print(f"成功获取数据，时间范围: {stock_data.index[0]} 到 {stock_data.index[-1]}")

    # ==================== 第二步：获取财报日期列表 ====================
    print("\n正在获取财报日期...")
    earnings_dates = get_stock_earnings_dates(stock_name)
    print(f"找到 {len(earnings_dates)} 个财报日期")

    # ==================== 第三步：逐次分析财报后的股价表现 ====================
    results = []
    for earnings_date in earnings_dates[:15]:  # 分析最近15次财报（约3-4年的数据）
        result = calculate_price_movement(stock_data, earnings_date, days_after=5)
        if result:
            results.append(result)

    # ==================== 第四步：整理并输出结果 ====================
    if results:
        # 将结果列表转换为 DataFrame，便于数据分析和输出
        df = pd.DataFrame(results)
        df = df.sort_values('财报日期', ascending=False)  # 按日期降序排列

        # 打印详细分析表格
        print("\n" + "=" * 100)
        print("历次财报发布后股价波动分析")
        print("=" * 100)
        print(df.to_string(index=False))

        # ==================== 第五步：输出统计摘要 ====================
        print("\n" + "=" * 100)
        print("统计摘要")
        print("=" * 100)

        # 财报日涨跌幅统计
        earnings_day_changes = df['财报日涨跌幅(%)'].dropna()
        print(f"\n财报发布日涨跌幅统计:")
        print(f"  平均涨跌幅: {earnings_day_changes.mean():.2f}%")      # 平均值：总体表现
        print(f"  中位数: {earnings_day_changes.median():.2f}%")      # 中位数：典型表现
        print(f"  标准差: {earnings_day_changes.std():.2f}%")         # 标准差：波动大小
        print(f"  上涨次数: {(earnings_day_changes > 0).sum()} 次")   # 正收益次数
        print(f"  下跌次数: {(earnings_day_changes < 0).sum()} 次")   # 负收益次数
        print(f"  上涨概率: {(earnings_day_changes > 0).sum() / len(earnings_day_changes) * 100:.1f}%")  # 胜率

        # 财报后第1个交易日统计
        if '第1日后涨跌幅(%)' in df.columns:
            day1_changes = df['第1日后涨跌幅(%)'].dropna()
            print(f"\n财报后第1个交易日累计涨跌幅统计:")
            print(f"  平均涨跌幅: {day1_changes.mean():.2f}%")
            print(f"  上涨概率: {(day1_changes > 0).sum() / len(day1_changes) * 100:.1f}%")

        # 财报后第5个交易日统计
        if '第5日后涨跌幅(%)' in df.columns:
            day5_changes = df['第5日后涨跌幅(%)'].dropna()
            print(f"\n财报后第5个交易日累计涨跌幅统计:")
            print(f"  平均涨跌幅: {day5_changes.mean():.2f}%")
            print(f"  上涨概率: {(day5_changes > 0).sum() / len(day5_changes) * 100:.1f}%")

        # ==================== 第六步：保存结果到文件 ====================
        output_file = f"{stock_name}_earnings_analysis.csv"
        # 使用 utf-8-sig 编码，确保中文在 Excel 中正确显示
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n详细数据已保存至: {output_file}")

        return df
    else:
        print("未能分析任何财报数据")
        return None


# ==================== 程序入口 ====================
if __name__ == "__main__":
    # 设置要分析的股票代码
    # 可选示例：MSFT（微软）、AAPL（苹果）、GOOGL（谷歌）、APP（AppLovin）
    stock_name = "APP"

    # 执行分析
    df = analyze_stock_earnings(stock_name)