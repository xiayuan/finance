"""
微软(stock)财报发布后股价波动分析
分析财报发布日及后续几个交易日的股价表现
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

from curl_cffi import requests

import os

proxy = 'http://30.172.114.63:5782'
os.environ['HTTP_PROXY'] = proxy
os.environ['HTTPS_PROXY'] = proxy

def get_stock_earnings_dates(stock_name):
    """
    获取微软财报发布日期
    使用yfinance获取历史财报日期
    """
    session = requests.Session(impersonate="chrome")
    stock = yf.Ticker(stock_name, session=session)


    # 获取财报日历
    earnings_dates = stock.earnings_dates

    if earnings_dates is not None and not earnings_dates.empty:
        # 按日期排序
        earnings_dates = earnings_dates.sort_index(ascending=False)
        # 处理夏令时歧义 - 将索引转换为不带时区的日期
        return [date.tz_localize(None) if hasattr(date, 'tz_localize') else date for date in earnings_dates.index.tolist()]
    else:
        print("无法自动获取财报日期，使用手动指定的日期")
        # 2024-2025年的部分财报日期（示例）
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

    参数:
    - stock_data: 股价数据
    - earnings_date: 财报发布日期
    - days_after: 计算发布后几天的波动

    返回:
    - 包含各种波动指标的字典
    """
    try:
        # 确保日期格式一致，并处理时区问题
        if hasattr(earnings_date, 'tz_localize'):
            earnings_date = earnings_date.tz_localize(None)
        earnings_date = pd.Timestamp(earnings_date).normalize()

        # 确保stock_data的索引也没有时区信息
        if stock_data.index.tz is not None:
            stock_data.index = stock_data.index.tz_localize(None)

        # 获取财报发布日的收盘价
        # 如果当天没有交易，找最近的交易日
        date_range = pd.date_range(
            start=earnings_date - timedelta(days=5),
            end=earnings_date + timedelta(days=1)
        )

        available_dates = stock_data.index.intersection(date_range)
        if len(available_dates) == 0:
            return None

        earnings_day = available_dates[-1]  # 最接近财报日的交易日

        # 获取财报前一个交易日的收盘价
        pre_dates = stock_data.index[stock_data.index < earnings_day]
        if len(pre_dates) == 0:
            return None
        pre_earnings_day = pre_dates[-1]

        # 获取财报后的交易日
        post_dates = stock_data.index[stock_data.index > earnings_day]

        if len(post_dates) == 0:
            return None

        # 价格数据
        pre_close = stock_data.loc[pre_earnings_day, 'Close']
        earnings_day_close = stock_data.loc[earnings_day, 'Close']

        # 计算各种波动指标
        result = {
            '财报日期': earnings_date.strftime('%Y-%m-%d'),
            '实际交易日': earnings_day.strftime('%Y-%m-%d'),
            '财报前收盘价': round(pre_close, 2),
            '财报日收盘价': round(earnings_day_close, 2),
            '财报日涨跌幅(%)': round((earnings_day_close - pre_close) / pre_close * 100, 2),
        }

        # 计算后续交易日的表现
        for day in range(1, min(days_after + 1, len(post_dates) + 1)):
            if day <= len(post_dates):
                future_day = post_dates[day - 1]
                future_close = stock_data.loc[future_day, 'Close']

                # 相对于财报前一日的涨跌幅
                change_pct = round((future_close - pre_close) / pre_close * 100, 2)
                result[f'第{day}日后涨跌幅(%)'] = change_pct

                if day == 1:
                    result[f'第{day}日后收盘价'] = round(future_close, 2)

        # 计算最大涨幅和最大跌幅
        if len(post_dates) >= days_after:
            period_data = stock_data.loc[
                earnings_day:post_dates[days_after - 1]
            ]
            max_price = period_data['High'].max()
            min_price = period_data['Low'].min()

            result['期间最高价'] = round(max_price, 2)
            result['期间最低价'] = round(min_price, 2)
            result['最大涨幅(%)'] = round((max_price - pre_close) / pre_close * 100, 2)
            result['最大跌幅(%)'] = round((min_price - pre_close) / pre_close * 100, 2)

        return result

    except Exception as e:
        print(f"处理 {earnings_date} 时出错: {e}")
        return None


def analyze_stock_earnings(stock_name):
    """
    主函数：分析微软财报发布后的股价波动
    """
    print("正在获取微软股票数据...")

    # 获取微软股票数据（最近3年）
    stock = yf.Ticker(stock_name)
    stock_data = stock.history(period="3y")

    if stock_data.empty:
        print("无法获取股票数据")
        return

    # 确保索引没有时区信息，避免夏令时问题
    if stock_data.index.tz is not None:
        stock_data.index = stock_data.index.tz_localize(None)

    print(f"成功获取数据，时间范围: {stock_data.index[0]} 到 {stock_data.index[-1]}")

    # 获取财报日期
    print("\n正在获取财报日期...")
    earnings_dates = get_stock_earnings_dates(stock_name)
    print(f"找到 {len(earnings_dates)} 个财报日期")

    # 分析每个财报日期的股价波动
    results = []
    for earnings_date in earnings_dates[:15]:  # 分析最近15次财报
        result = calculate_price_movement(stock_data, earnings_date, days_after=5)
        if result:
            results.append(result)

    # 转换为DataFrame并显示
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values('财报日期', ascending=False)

        print("\n" + "=" * 100)
        print("历次财报发布后股价波动分析")
        print("=" * 100)
        print(df.to_string(index=False))

        # 统计分析
        print("\n" + "=" * 100)
        print("统计摘要")
        print("=" * 100)

        earnings_day_changes = df['财报日涨跌幅(%)'].dropna()
        print(f"\n财报发布日涨跌幅统计:")
        print(f"  平均涨跌幅: {earnings_day_changes.mean():.2f}%")
        print(f"  中位数: {earnings_day_changes.median():.2f}%")
        print(f"  标准差: {earnings_day_changes.std():.2f}%")
        print(f"  上涨次数: {(earnings_day_changes > 0).sum()} 次")
        print(f"  下跌次数: {(earnings_day_changes < 0).sum()} 次")
        print(f"  上涨概率: {(earnings_day_changes > 0).sum() / len(earnings_day_changes) * 100:.1f}%")

        if '第1日后涨跌幅(%)' in df.columns:
            day1_changes = df['第1日后涨跌幅(%)'].dropna()
            print(f"\n财报后第1个交易日累计涨跌幅统计:")
            print(f"  平均涨跌幅: {day1_changes.mean():.2f}%")
            print(f"  上涨概率: {(day1_changes > 0).sum() / len(day1_changes) * 100:.1f}%")

        if '第5日后涨跌幅(%)' in df.columns:
            day5_changes = df['第5日后涨跌幅(%)'].dropna()
            print(f"\n财报后第5个交易日累计涨跌幅统计:")
            print(f"  平均涨跌幅: {day5_changes.mean():.2f}%")
            print(f"  上涨概率: {(day5_changes > 0).sum() / len(day5_changes) * 100:.1f}%")

        # 保存结果
        output_file = f"{stock_name}_earnings_analysis.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n详细数据已保存至: {output_file}")

        return df
    else:
        print("未能分析任何财报数据")
        return None


if __name__ == "__main__":
    # 运行分析
    stock_name = "APP"
    df = analyze_stock_earnings(stock_name)