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
import logging
import sys
import time

from web3 import Web3, HTTPProvider

from market_maker_stats.pnl import get_approx_vwaps, pnl_text, pnl_chart
from market_maker_stats.zrx import zrx_trades
from market_maker_stats.util import get_block_timestamp, sort_trades_for_pnl, get_gdax_prices, get_prices
from pymaker import Address
from pymaker.zrx import ZrxExchange


class ZrxMarketMakerPnl:
    """Tool to calculate profitability for the 0x market maker keeper."""

    def __init__(self, args: list):
        parser = argparse.ArgumentParser(prog='0x-market-maker-pnl')
        parser.add_argument("--rpc-host", help="JSON-RPC host (default: `localhost')", default="localhost", type=str)
        parser.add_argument("--rpc-port", help="JSON-RPC port (default: `8545')", default=8545, type=int)
        parser.add_argument("--rpc-timeout", help="JSON-RPC timeout (in seconds, default: 60)", type=int, default=60)
        parser.add_argument("--exchange-address", help="Ethereum address of the 0x contract", required=True, type=str)
        parser.add_argument("--market-maker-address", help="Ethereum account of the market maker to analyze", required=True, type=str)
        parser.add_argument("--gdax-price", help="GDAX product (ETH-USD, BTC-USD) to use as the price history source", type=str)
        parser.add_argument("--price-feed", help="Price endpoint to use as the price history source", type=str)
        parser.add_argument("--price-history-file", help="File to use as the price history source", type=str)
        parser.add_argument("--vwap-minutes", help="Rolling VWAP window size (default: 240)", type=int, default=240)
        parser.add_argument("--buy-token", help="Name of the buy token", required=True, type=str)
        parser.add_argument("--buy-token-address", help="Ethereum address of the buy token", required=True, type=str)
        parser.add_argument("--buy-token-decimals", help="Number of decimals for the buy token", type=int, default=18)
        parser.add_argument("--sell-token", help="Name of the sell token", required=True, type=str)
        parser.add_argument("--sell-token-address", help="Ethereum address of the sell token", required=True, type=str)
        parser.add_argument("--sell-token-decimals", help="Number of decimals for the sell token", type=int, default=18)
        parser.add_argument("--old-sell-token-address", help="Ethereum address of the old sell token", required=False, type=str)
        parser.add_argument("--past-blocks", help="Number of past blocks to analyze", required=True, type=int)
        parser.add_argument("-o", "--output", help="File to save the chart or the table to", required=False, type=str)

        parser_mode = parser.add_mutually_exclusive_group(required=True)
        parser_mode.add_argument('--text', help="Show PnL as a text table", dest='text', action='store_true')
        parser_mode.add_argument('--chart', help="Show PnL on a cumulative graph", dest='chart', action='store_true')

        self.arguments = parser.parse_args(args)

        self.web3 = Web3(HTTPProvider(endpoint_uri=f"http://{self.arguments.rpc_host}:{self.arguments.rpc_port}",
                                      request_kwargs={'timeout': self.arguments.rpc_timeout}))
        self.infura = Web3(HTTPProvider(endpoint_uri=f"https://mainnet.infura.io/", request_kwargs={'timeout': 120}))
        self.buy_token_address = Address(self.arguments.buy_token_address)
        self.sell_token_address = Address(self.arguments.sell_token_address)
        self.old_sell_token_address = Address(self.arguments.old_sell_token_address) if self.arguments.old_sell_token_address else None
        self.sell_token_addresses = list(filter(lambda address: address is not None, [self.sell_token_address, self.old_sell_token_address]))
        self.market_maker_address = Address(self.arguments.market_maker_address)
        self.exchange = ZrxExchange(web3=self.web3, address=Address(self.arguments.exchange_address))

        if self.arguments.chart and self.arguments.output:
            import matplotlib
            matplotlib.use('Agg')

        logging.basicConfig(format='%(asctime)-15s %(levelname)-8s %(message)s', level=logging.INFO)
        logging.getLogger("filelock").setLevel(logging.WARNING)

    def main(self):
        start_timestamp = get_block_timestamp(self.infura, self.web3.eth.blockNumber - self.arguments.past_blocks)
        end_timestamp = int(time.time())

        events = self.exchange.past_fill(self.arguments.past_blocks, {'maker': self.market_maker_address.address})
        trades = zrx_trades(self.infura, self.market_maker_address, self.arguments.buy_token, self.buy_token_address, self.arguments.buy_token_decimals, self.arguments.sell_token, self.sell_token_addresses, self.arguments.sell_token_decimals, events, '-')
        trades = sort_trades_for_pnl(trades)

        prices = get_prices(self.arguments.gdax_price, self.arguments.price_feed, self.arguments.price_history_file, start_timestamp, end_timestamp)
        vwaps = get_approx_vwaps(prices, self.arguments.vwap_minutes)
        vwaps_start = prices[0].timestamp

        if self.arguments.text:
            pnl_text(trades, vwaps, vwaps_start, self.arguments.buy_token, self.arguments.sell_token, self.arguments.vwap_minutes, self.arguments.output)

        if self.arguments.chart:
            pnl_chart(start_timestamp, end_timestamp, prices, trades, vwaps, vwaps_start, self.arguments.buy_token, self.arguments.sell_token, self.arguments.output)


if __name__ == '__main__':
    ZrxMarketMakerPnl(sys.argv[1:]).main()
