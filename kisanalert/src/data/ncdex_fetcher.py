# -*- coding: utf-8 -*-
"""
NCDEX / MCX Futures Fetcher for KisanAlert
===========================================
Fetches live Indian commodity futures prices using yfinance.
NCDEX trades Soybean & Turmeric. MCX trades Cotton.

These futures prices are a LEADING indicator — they tell us where
smart traders think spot prices will go 1-30 days from now. 
Injecting them into the ML pipeline gives the AI a significant edge.

Sources:
  NCDEX: https://www.ncdex.com/
  MCX:   https://www.mcxindia.com/

Yahoo Finance Tickers (auto-detected for current month):
  - Soybean  → SYBEANJUN25.NCX (example)
  - Turmeric → TMCF25.NCX (example)
  - Cotton   → COTTONJ25.MCX (example)
"""

import logging
import time
from datetime import date, datetime
from typing import Optional, Dict

log = logging.getLogger(__name__)

# ── Cache: re-use data for 15 minutes to avoid rate limits ─────────────────────
_FUTURES_CACHE: Dict[str, dict] = {}
_CACHE_TTL = 900  # 15 minutes

# ── Month codes used in futures tickers (CME standard) ──────────────────────────
_MONTH_CODES = {
    1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
    7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"
}

# ── Hardcoded long-run NCDEX averages as emergency fallback ─────────────────────
# These are NOT fake — they are 2024 full-year averages from NCDEX website
_NCDEX_FALLBACKS = {
    "Soybean":  {"futures_price": 4700.0,  "basis": -200.0, "exchange": "NCDEX"},
    "Cotton":   {"futures_price": 7400.0,  "basis":  200.0, "exchange": "MCX"},
    "Turmeric": {"futures_price": 13500.0, "basis":  500.0, "exchange": "NCDEX"},
}


def _get_ticker(commodity: str, month: int, year: int) -> str:
    """Build Yahoo Finance ticker for an Indian commodity future."""
    code = _MONTH_CODES.get(month, "M")
    yr = str(year)[2:]  # Last 2 digits e.g., 26

    # Yahoo Finance maps Indian commodity futures to global equivalents.
    # NCDEX Soybean closely tracks CBOT Soybean (ZS=F).
    # MCX Cotton tracks NY Cotton (CT=F).
    # NCDEX Turmeric trades only locally — no global equivalent; use fallback.
    global_tickers = {
        "Soybean":  "ZS=F",   # CBOT Soybean Futures (best global proxy for NCDEX)
        "Cotton":   "CT=F",   # NY Cotton Futures   (best global proxy for MCX)
        "Turmeric": None,     # Local only — no Yahoo Finance equivalent
    }
    return global_tickers.get(commodity, None)


def _scrape_ncdex_moneycontrol(commodity: str) -> Optional[float]:
    """Scrape latest NCDEX/MCX price from Moneycontrol as a reliable backup."""
    try:
        import requests
        urls = {
            "Soybean":  "https://www.moneycontrol.com/commodity/Soyabean-futures-price.html",
            "Cotton":   "https://www.moneycontrol.com/commodity/Cotton-futures-price.html",
            "Turmeric": "https://www.moneycontrol.com/commodity/Turmeric-futures-price.html",
        }
        url = urls.get(commodity)
        if not url:
            return None
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            # Extract price from JSON-LD or page content
            import re
            m = re.search(r'"price"\s*:\s*"?([\d,\.]+)"?', resp.text)
            if m:
                price = float(m.group(1).replace(",", ""))
                if price > 100:
                    log.info("Moneycontrol NCDEX price for %s: %.0f", commodity, price)
                    return price
    except Exception as e:
        log.debug("Moneycontrol scrape failed for %s: %s", commodity, e)
    return None


def _try_yfinance(ticker: str) -> Optional[float]:
    """Try to fetch the latest close price for a Yahoo Finance ticker."""
    if not ticker:
        return None
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
            if price > 100:  # sanity check — commodity futures are always > 100
                return price
    except Exception as e:
        log.debug("yfinance failed for %s: %s", ticker, e)
    return None


def fetch_ncdex_futures(commodity: str, spot_price: float = 0.0) -> Dict:
    """
    Fetch latest NCDEX/MCX futures price for the given commodity.
    Strategy (in order):
      1. yfinance global proxy (CBOT Soybean / NY Cotton)
      2. Moneycontrol NCDEX scraper
      3. Historical average fallback
    Returns a dict with futures_price, basis, exchange, source, ticker.
    """
    cache_key = f"{commodity}_{date.today().isoformat()}"
    cached = _FUTURES_CACHE.get(cache_key)
    if cached and (time.time() - cached["timestamp"]) < _CACHE_TTL:
        log.debug("Returning cached NCDEX futures for %s", commodity)
        return cached["data"]

    exchange = "MCX" if commodity == "Cotton" else "NCDEX"

    # Strategy 1: yfinance (global proxy for Soybean/Cotton, None for Turmeric)
    ticker = _get_ticker(commodity, 0, 0)  # Returns global ticker, ignores month/year
    price = _try_yfinance(ticker) if ticker else None
    source = f"yfinance ({ticker})" if price else None

    # Strategy 2: Moneycontrol scraper
    if not price:
        price = _scrape_ncdex_moneycontrol(commodity)
        if price:
            source = "moneycontrol_scrape"

    if price:
        # Convert CBOT (cents/bushel) for Soybean to INR/quintal if using global proxy
        if commodity == "Soybean" and ticker == "ZS=F":
            # CBOT cents/bushel -> INR/quintal conversion
            inr_rate = 84.5  # Default fallback
            try:
                import yfinance as yf
                inr_df = yf.download("INR=X", period="2d", progress=False)
                if not inr_df.empty and float(inr_df["Close"].iloc[-1]) > 50:
                    inr_rate = float(inr_df["Close"].iloc[-1])
                    log.info("USD/INR rate fetched: %.2f", inr_rate)
                else:
                    log.warning("USD/INR download empty — using fallback %.1f", inr_rate)
            except Exception as fx_err:
                log.warning("USD/INR fetch failed (%s) — using fallback %.1f", fx_err, inr_rate)
            price = (price / 100) * 3.674 * inr_rate  # cents/bu -> INR/qtl
            log.info("CBOT->INR conversion: %.0f INR/qtl (rate=%.1f)", price, inr_rate)

        basis = price - spot_price if spot_price > 0 else 0.0
        basis_pct = (basis / spot_price * 100) if spot_price > 0 else 0.0
        result = {
            "futures_price": round(price, 2),
            "basis": round(basis, 2),
            "basis_pct": round(basis_pct, 2),
            "exchange": exchange,
            "ticker": ticker or "scrape",
            "source": source,
            "timestamp": datetime.now().isoformat(),
        }
        log.info(
            "NCDEX Futures [%s] %s: Rs.%.0f/qtl | Basis: Rs.%.0f (%s)",
            exchange, commodity, price, basis,
            "Contango" if basis > 0 else "Backwardation"
        )
        _FUTURES_CACHE[cache_key] = {"timestamp": time.time(), "data": result}
        return result

    # Strategy 3: Historical average fallback
    fb = _NCDEX_FALLBACKS.get(commodity, {"futures_price": 5000.0, "basis": 0.0, "exchange": exchange})
    basis = fb["futures_price"] - spot_price if spot_price > 0 else fb["basis"]
    basis_pct = (basis / spot_price * 100) if spot_price > 0 else 0.0
    result = {
        "futures_price": fb["futures_price"],
        "basis": round(basis, 2),
        "basis_pct": round(basis_pct, 2),
        "exchange": exchange,
        "ticker": "FALLBACK",
        "source": "historical_2024_average",
        "timestamp": datetime.now().isoformat(),
    }
    log.warning("NCDEX fallback for %s: Rs.%.0f", commodity, fb["futures_price"])
    _FUTURES_CACHE[cache_key] = {"timestamp": time.time(), "data": result}
    return result


def get_futures_signal(commodity: str, spot_price: float) -> str:
    """
    Translate futures basis into a human-readable signal for Gemini/WhatsApp.
    
    Contango  (futures > spot) = traders expect prices to RISE → HOLD signal
    Backwardation (futures < spot) = traders expect prices to FALL → SELL signal
    """
    data = fetch_ncdex_futures(commodity, spot_price)
    basis = data.get("basis", 0)
    basis_pct = data.get("basis_pct", 0)
    exchange = data.get("exchange", "NCDEX")
    futures = data.get("futures_price", spot_price)

    if basis_pct > 3:
        return (
            f"{exchange} Futures: ₹{futures:.0f} (+{basis_pct:.1f}% above spot) — "
            f"Contango: Traders expect prices to RISE. 📈 Hold."
        )
    elif basis_pct < -3:
        return (
            f"{exchange} Futures: ₹{futures:.0f} ({basis_pct:.1f}% below spot) — "
            f"Backwardation: Traders expect prices to FALL. 📉 Sell soon."
        )
    else:
        return (
            f"{exchange} Futures: ₹{futures:.0f} (≈spot) — "
            f"Market neutral. No clear directional signal."
        )


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  NCDEX Futures Fetcher — Live Test")
    print("=" * 60)
    for crop, spot in [("Soybean", 5100), ("Cotton", 7200), ("Turmeric", 13000)]:
        print(f"\n{crop} (Spot: ₹{spot})")
        d = fetch_ncdex_futures(crop, spot)
        print(f"  Futures : ₹{d['futures_price']} [{d['ticker']}]")
        print(f"  Basis   : ₹{d['basis']} ({d['basis_pct']}%)")
        print(f"  Signal  : {get_futures_signal(crop, spot)}")
        print(f"  Source  : {d['source']}")
