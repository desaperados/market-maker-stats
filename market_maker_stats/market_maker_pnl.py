# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2017-2018 reverendus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import sys
import time

from market_maker_stats.pnl import get_approx_vwaps, pnl_text, pnl_chart
from market_maker_stats.util import to_seconds, sort_trades_for_pnl, initialize_logging, get_prices, get_trades


class MarketMakerPnl:
    """Tool to calculate profitability for market maker keepers."""

    def __init__(self, args: list):
        parser = argparse.ArgumentParser(prog='market-maker-pnl')
        parser.add_argument("--gdax-price", help="GDAX product (ETH-USD, BTC-USD) to use as the price history source", type=str)
        parser.add_argument("--price-feed", help="Price endpoint to use as the price history source", type=str)
        parser.add_argument("--price-history-file", help="File to use as the price history source", type=str)
        parser.add_argument("--vwap-minutes", help="Rolling VWAP window size (default: 240)", type=int, default=240)
        parser.add_argument("--our-trades", help="Trades endpoint from which to fetch our trades", required=True, type=str)
        parser.add_argument("--buy-token", help="Name of the buy token", required=True, type=str)
        parser.add_argument("--sell-token", help="Name of the sell token", required=True, type=str)
        parser.add_argument("--past", help="Past period of time for which to get the trades for (e.g. 3d)", required=True, type=str)
        parser.add_argument("-o", "--output", help="File to save the chart or the table to", required=False, type=str)

        parser_mode = parser.add_mutually_exclusive_group(required=True)
        parser_mode.add_argument('--text', help="Show PnL as a text table", dest='text', action='store_true')
        parser_mode.add_argument('--chart', help="Show PnL on a cumulative graph", dest='chart', action='store_true')

        self.arguments = parser.parse_args(args)

        if self.arguments.chart and self.arguments.output:
            import matplotlib
            matplotlib.use('Agg')

        initialize_logging()

    def main(self):
        start_timestamp = int(time.time() - to_seconds(self.arguments.past))
        end_timestamp = int(time.time())

        trades = sort_trades_for_pnl(get_trades(self.arguments.our_trades, start_timestamp, end_timestamp))
        prices = get_prices(self.arguments.gdax_price, self.arguments.price_feed, self.arguments.price_history_file, start_timestamp, end_timestamp)
        vwaps = get_approx_vwaps(prices, self.arguments.vwap_minutes)
        vwaps_start = prices[0].timestamp

        if self.arguments.text:
            pnl_text(trades, vwaps, vwaps_start, self.arguments.buy_token, self.arguments.sell_token, self.arguments.vwap_minutes, self.arguments.output)

        if self.arguments.chart:
            pnl_chart(start_timestamp, end_timestamp, prices, trades, vwaps, vwaps_start, self.arguments.buy_token, self.arguments.sell_token, self.arguments.output)


if __name__ == '__main__':
    MarketMakerPnl(sys.argv[1:]).main()
