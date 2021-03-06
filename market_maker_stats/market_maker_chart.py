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

from market_maker_stats.chart import initialize_charting, draw_chart, prepare_order_history_for_charting
from market_maker_stats.util import to_seconds, initialize_logging, get_prices, get_trades, get_order_history


class MarketMakerChart:
    """Tool to generate a chart displaying market maker keeper price feed history and trades."""

    def __init__(self, args: list):
        parser = argparse.ArgumentParser(prog='market-maker-chart')
        parser.add_argument("--gdax-price", help="GDAX product (ETH-USD, BTC-USD) to use as the price history source", type=str)
        parser.add_argument("--price-feed", help="Price endpoint to use as the price history source", type=str)
        parser.add_argument("--alternative-price-feed", help="Price endpoint to use as the alternative price history source", type=str)
        parser.add_argument("--price-gap-size", help="Minimum gap which will be considered as price missing", default=180, type=int)
        parser.add_argument("--order-history", help="Order history endpoint from which to fetch our order history", type=str)
        parser.add_argument("--our-trades", help="Trades endpoint from which to fetch our trades", type=str)
        parser.add_argument("--all-trades", help="Trades endpoint from which to fetch all market trades", type=str)
        parser.add_argument("--past", help="Past period of time for which to draw the chart for (e.g. 3d)", required=True, type=str)
        parser.add_argument("-o", "--output", help="Name of the filename to save to chart to."
                                                   " Will get displayed on-screen if empty", required=False, type=str)
        self.arguments = parser.parse_args(args)

        initialize_charting(self.arguments.output)
        initialize_logging()

    def main(self):
        start_timestamp = int(time.time() - to_seconds(self.arguments.past))
        end_timestamp = int(time.time())

        our_trades = get_trades(self.arguments.our_trades, start_timestamp, end_timestamp)
        all_trades = get_trades(self.arguments.all_trades, start_timestamp, end_timestamp)

        prices = get_prices(self.arguments.gdax_price, self.arguments.price_feed, None, start_timestamp, end_timestamp)
        alternative_prices = get_prices(None, self.arguments.alternative_price_feed, None, start_timestamp, end_timestamp)

        order_history = get_order_history(self.arguments.order_history, start_timestamp, end_timestamp)
        order_history = prepare_order_history_for_charting(order_history)

        draw_chart(start_timestamp, end_timestamp, prices, alternative_prices, self.arguments.price_gap_size, order_history, our_trades, all_trades, self.arguments.output)


if __name__ == '__main__':
    MarketMakerChart(sys.argv[1:]).main()
