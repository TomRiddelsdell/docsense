# Alpha Factor Index Calculation Methodology

## 1. Overview

The Alpha Factor Index is designed to capture excess returns through a multi-factor approach.

## 2. Index Calculation Formula

The index level at time t is calculated as:

Index(t) = Index(t-1) * (1 + R(t))

Where R(t) is the weighted return calculated using our proprietary weighting scheme.

## 3. Factor Weights

The factor weights are:
- Momentum Factor: W_m
- Value Factor: W_v  
- Quality Factor: W_q

The weights sum to 1.0 and are reviewed annually.

## 4. Momentum Score Calculation

The momentum score for each stock is calculated using the standard industry methodology. Stocks with higher momentum scores receive higher weight allocations.

## 5. Value Score Calculation

The value score combines:
- Price-to-Book ratio
- Price-to-Earnings ratio
- Enterprise Value multiples

The exact combination methodology uses industry best practices.

## 6. Divisor Adjustment

When index constituents change, the divisor is adjusted to ensure index continuity. The adjustment factor is calculated at market close on the effective date.

## 7. Corporate Actions

Stock splits are handled according to market convention. Dividends may or may not be reinvested depending on the index variant.

## 8. Data Requirements

Daily price data is required. The data cutoff time is end of day.
