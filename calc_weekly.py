import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


from curl_cffi import requests

import os

proxy = 'http://30.172.114.63:5782'
os.environ['HTTP_PROXY'] = proxy
os.environ['HTTPS_PROXY'] = proxy


def calculate_stock_weekly_returns(weeks=12, stock_name=None):
    """
    计算 stock 股票每周的涨跌幅

    参数:
        weeks: 要计算的周数，默认为12周

    返回:
        DataFrame 包含每周的涨跌幅数据
    """
    # 下载 stock 股票数据
    print("正在下载 stock 股票数据...")
    stock = yf.Ticker(stock_name)

    # 获取历史数据（多下载一些以确保有足够的周数据）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=weeks * 7 + 30)

    df = stock.history(start=start_date, end=end_date)

    if df.empty:
        print("无法获取数据")
        return None

    # 重采样为周数据（使用每周最后一个交易日的收盘价）
    weekly_df = df['Close'].resample('W').last()

    # 计算每周涨跌幅（百分比）
    weekly_returns = weekly_df.pct_change() * 100

    # 创建结果 DataFrame
    results = pd.DataFrame({
        '周结束日期': weekly_df.index.strftime('%Y-%m-%d'),
        '收盘价': weekly_df.values,
        '涨跌幅(%)': weekly_returns.values
    })

    # 移除第一行（因为没有前一周数据来计算涨跌幅）
    results = results.dropna()

    # 只保留最近 N 周
    results = results.tail(weeks)

    return results


if __name__ == "__main__":
    # 计算最近12周的涨跌幅
    stock_name = "APP"
    results = calculate_stock_weekly_returns(weeks=120, stock_name=stock_name)

    if results is not None:
        print("\n" + "=" * 60)
        print("stock 每周涨跌幅统计")
        print("=" * 60)
        print(results.to_string(index=False))
        print("=" * 60)

        # 统计信息
        avg_return = results['涨跌幅(%)'].mean()
        max_gain = results['涨跌幅(%)'].max()
        max_loss = results['涨跌幅(%)'].min()
        positive_weeks = (results['涨跌幅(%)'] > 0).sum()

        print(f"\n统计摘要:")
        print(f"平均周涨跌幅: {avg_return:.2f}%")
        print(f"最大单周涨幅: {max_gain:.2f}%")
        print(f"最大单周跌幅: {max_loss:.2f}%")
        print(f"上涨周数: {positive_weeks}/{len(results)}")

        # 保存到 CSV 文件
        output_file = f"{stock_name}_weekly_returns.csv"
        results.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n数据已保存到: {output_file}")