"""markets-service 入口"""
import argparse
import logging
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Markets Data Service")
    parser.add_argument("command", choices=["test", "collect", "pricing"], help="命令")
    parser.add_argument("--provider", default="yfinance", help="数据源")
    parser.add_argument("--symbol", default="AAPL", help="标的代码")
    parser.add_argument("--market", default="us_stock", help="市场类型")
    args = parser.parse_args()
    
    if args.command == "test":
        from providers import ccxt, akshare, yfinance, baostock, fredapi, openbb
        from core.registry import ProviderRegistry
        
        logger.info("已注册的 Providers: %s", ProviderRegistry.list_providers())
        
        fetcher_cls = ProviderRegistry.get(args.provider, "candle")
        if fetcher_cls:
            fetcher = fetcher_cls()
            data = fetcher.fetch_sync(market=args.market, symbol=args.symbol, limit=5)
            logger.info("获取到 %d 条数据", len(data))
            for d in data[:3]:
                logger.info("  %s", d)
        else:
            logger.error("未找到 Provider: %s", args.provider)
    
    elif args.command == "pricing":
        from providers.quantlib import OptionPricer
        from datetime import date, timedelta
        
        pricer = OptionPricer(risk_free_rate=0.05)
        greeks = pricer.price_european(
            spot=100, strike=100,
            expiry=date.today() + timedelta(days=30),
            volatility=0.2, option_type="call"
        )
        logger.info("期权定价 (ATM Call, 30天到期, IV=20%%):")
        logger.info("  价格: %.4f", greeks.price)
        logger.info("  Delta: %.4f, Gamma: %.4f", greeks.delta, greeks.gamma)
        logger.info("  Theta: %.4f, Vega: %.4f", greeks.theta, greeks.vega)
    
    elif args.command == "collect":
        logger.info("启动数据采集...")


if __name__ == "__main__":
    main()
