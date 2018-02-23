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
import datetime
import json
import logging
import sys
from typing import List

import pytz
from texttable import Texttable
from web3 import Web3, HTTPProvider

from market_maker_stats.zrx import zrx_trades, Trade
from market_maker_stats.util import format_timestamp, sort_trades
from pymaker import Address
from pymaker.zrx import ZrxExchange


class ZrxMarketMakerTrades:
    """Tool to list historical trades for the 0x market maker keeper."""

    def __init__(self, args: list):
        parser = argparse.ArgumentParser(prog='0x-market-maker-trades')
        parser.add_argument("--rpc-host", help="JSON-RPC host (default: `localhost')", default="localhost", type=str)
        parser.add_argument("--rpc-port", help="JSON-RPC port (default: `8545')", default=8545, type=int)
        parser.add_argument("--rpc-timeout", help="JSON-RPC timeout (in seconds, default: 60)", type=int, default=60)
        parser.add_argument("--exchange-address", help="Ethereum address of the 0x contract", required=True, type=str)
        parser.add_argument("--sai-address", help="Ethereum address of the SAI token", required=True, type=str)
        parser.add_argument("--weth-address", help="Ethereum address of the WETH token", required=True, type=str)
        parser.add_argument("--old-weth-address", help="Ethereum address of the old WETH token", required=True, type=str)
        parser.add_argument("--market-maker-address", help="Ethereum account of the market maker to analyze", required=True, type=str)
        parser.add_argument("--past-blocks", help="Number of past blocks to analyze", required=True, type=int)
        parser.add_argument("-o", "--output", help="Name of the filename to save to chart to."
                                                   " Will get displayed on-screen if empty", required=False, type=str)

        parser_mode = parser.add_mutually_exclusive_group(required=True)
        parser_mode.add_argument('--text', help="List trades as a text table", dest='text', action='store_true')
        parser_mode.add_argument('--json', help="List trades as a JSON document", dest='json', action='store_true')

        self.arguments = parser.parse_args(args)

        self.web3 = Web3(HTTPProvider(endpoint_uri=f"http://{self.arguments.rpc_host}:{self.arguments.rpc_port}",
                                      request_kwargs={'timeout': self.arguments.rpc_timeout}))
        self.infura = Web3(HTTPProvider(endpoint_uri=f"https://mainnet.infura.io/", request_kwargs={'timeout': 120}))
        self.sai_address = Address(self.arguments.sai_address)
        self.weth_address = Address(self.arguments.weth_address)
        self.old_weth_address = Address(self.arguments.old_weth_address)
        self.market_maker_address = Address(self.arguments.market_maker_address)
        self.exchange = ZrxExchange(web3=self.web3, address=Address(self.arguments.exchange_address))

        logging.basicConfig(format='%(asctime)-15s %(levelname)-8s %(message)s', level=logging.INFO)
        logging.getLogger("filelock").setLevel(logging.WARNING)

    def token_pair(self):
        return "ETH/DAI"

    def base_token(self):
        return "ETH"

    def quote_token(self):
        return "DAI"

    def main(self):
        past_fills = self.exchange.past_fill(self.arguments.past_blocks, {'maker': self.market_maker_address.address})
        trades = zrx_trades(self.infura, self.market_maker_address, self.sai_address, [self.weth_address, self.old_weth_address], past_fills)
        trades = sort_trades(trades)

        if self.arguments.text:
            self.text_trades(trades)
        elif self.arguments.json:
            self.json_trades(trades)
        else:
            raise Exception("Unknown output mode")

    def json_trades(self, trades: List[Trade]):
        assert(isinstance(trades, list))

        def build_item(trade: Trade) -> dict:
            return {
                'datetime': format_timestamp(trade.timestamp),
                'timestamp': trade.timestamp,
                'type': "Sell" if trade.is_sell else "Buy",
                'price': float(trade.price),
                'amount': float(trade.amount),
                'money': float(trade.money),
                'taker': str(trade.taker)
            }

        print(json.dumps(list(map(build_item, trades)), indent=True))

    def text_trades(self, trades: List[Trade]):
        assert(isinstance(trades, list))

        def table_row(trade: Trade) -> list:
            return [format_timestamp(trade.timestamp),
                    "Sell" if trade.is_sell else "Buy",
                    format(float(trade.price), '.8f'),
                    format(float(trade.amount), '.8f'),
                    format(float(trade.money), '.8f'),
                    str(trade.taker)]

        table = Texttable(max_width=250)
        table.set_deco(Texttable.HEADER)
        table.set_cols_dtype(['t', 't', 't', 't', 't', 't'])
        table.set_cols_align(['l', 'l', 'r', 'r', 'r', 'l'])
        table.add_rows([["Date/time",
                         "Type",
                         "Price",
                         f"Amount in {self.base_token()}",
                         f"Value in {self.quote_token()}",
                         f"Taker"]] + list(map(table_row, trades)))

        print(f"Trade history on the {self.token_pair()} pair:")
        print(f"")
        print(table.draw())
        print(f"")
        print(f"Buy  = Somebody bought {self.quote_token()} from the keeper")
        print(f"Sell = Somebody sold {self.quote_token()} to the keeper")
        print(f"")
        print(f"Number of trades: {len(trades)}")
        print(f"Generated at: {datetime.datetime.now(tz=pytz.UTC).strftime('%Y.%m.%d %H:%M:%S %Z')}")


if __name__ == '__main__':
    ZrxMarketMakerTrades(sys.argv[1:]).main()