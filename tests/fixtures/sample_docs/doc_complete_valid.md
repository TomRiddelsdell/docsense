# Simple Price Index Methodology

## 1. Overview

The Simple Price Index tracks the price performance of 10 specified large-cap US stocks. This document contains all information necessary to independently calculate and maintain the index.

## 2. Index Constituents

The index consists of exactly 10 stocks with the following tickers:
1. AAPL - Apple Inc.
2. MSFT - Microsoft Corporation
3. GOOGL - Alphabet Inc. Class A
4. AMZN - Amazon.com Inc.
5. META - Meta Platforms Inc.
6. NVDA - NVIDIA Corporation
7. TSLA - Tesla Inc.
8. BRK.B - Berkshire Hathaway Inc. Class B
9. JPM - JPMorgan Chase & Co.
10. JNJ - Johnson & Johnson

## 3. Index Calculation Formula

The index level at time t is calculated as:

```
Index(t) = (Sum of all constituent prices at time t) / Divisor
```

Where:
- Sum = P_AAPL + P_MSFT + P_GOOGL + P_AMZN + P_META + P_NVDA + P_TSLA + P_BRK.B + P_JPM + P_JNJ
- Divisor = Initial divisor adjusted for corporate actions
- Initial Divisor = 100.00 (set on base date)

Base Date: January 2, 2020
Base Value: 1000.00

## 4. Data Source Specification

Price data is sourced from NYSE/NASDAQ official closing prices as published on their respective websites:
- NYSE: https://www.nyse.com/market-data/historical
- NASDAQ: https://www.nasdaq.com/market-activity/quotes/historical

Calculation Timing:
- End-of-day index value calculated at 4:00 PM ET
- Uses official closing prices

## 5. Corporate Actions Handling

### 5.1 Stock Splits
When a stock split occurs (e.g., 4-for-1):
```
New Divisor = Old Divisor * (Sum of prices after split) / (Sum of prices before split)
```

### 5.2 Cash Dividends
This is a price return index. Cash dividends are NOT reinvested.

### 5.3 Constituent Changes
If a constituent is removed (delisting, acquisition):
1. The stock is removed at its last trading price
2. Divisor is adjusted: New Divisor = Old Divisor * (New Sum) / (Old Sum)
3. No replacement is added (index becomes 9-stock index)

## 6. Rebalancing

There is no periodic rebalancing. Constituents are fixed unless a corporate event forces removal.

## 7. Governance

Changes to this methodology require:
1. Written proposal submitted to index@example.com
2. 30-day public comment period
3. Approval by Index Administrator
4. 60-day notice before implementation

Index Administrator: Example Index Services LLC
Address: 123 Financial Street, New York, NY 10001
Email: index@example.com
Phone: +1 (555) 123-4567

## 8. Calculation Example

As of January 2, 2020 (Base Date):
- AAPL: $75.00
- MSFT: $160.00
- GOOGL: $1,350.00
- AMZN: $1,850.00
- META: $205.00
- NVDA: $240.00
- TSLA: $85.00
- BRK.B: $225.00
- JPM: $140.00
- JNJ: $145.00

Sum = $4,475.00
Divisor = 4.475 (calculated to achieve base value of 1000.00)

Index(base) = $4,475.00 / 4.475 = 1000.00 ✓

## 9. Publication

Index values are published daily at:
- Website: https://example.com/simple-price-index
- Format: CSV with columns [Date, Open, High, Low, Close]
- Historical data available from base date

## 10. Contact Information

For questions about this methodology:
- Email: index@example.com
- Phone: +1 (555) 123-4567
- Hours: 9:00 AM - 5:00 PM ET, Monday-Friday
