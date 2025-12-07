# Sector Rotation Strategy Index - Methodology v2.1

## 1. Overview

This document describes the methodology for the Sector Rotation Strategy Index, which dynamically allocates across sectors based on momentum signals.

Version: 2.1
Effective Date: January 2024

## 2. Sector Universe

The index rotates among 11 GICS sectors. Sector exposure is implemented through sector ETFs.

## 3. Signal Calculation

The momentum signal is calculated using 12-month total return for each sector.

[Note: As per the Index Committee meeting on March 15, 2024, the signal calculation was updated to use 6-month returns instead of 12-month returns. See Amendment A below.]

## 4. Allocation Rules

The top 3 sectors by momentum signal receive equal weight (33.33% each). All other sectors receive zero weight.

## 5. Rebalancing

Monthly rebalancing occurs on the last business day of each month.

[Note: Section 3.2 of the Quick Reference Guide states rebalancing is semi-annual. Please verify the correct frequency.]

## 6. Amendment A - March 2024 Update

The signal lookback period is hereby changed from 12 months to 6 months, effective April 1, 2024.

However, for risk management purposes, the 12-month signal continues to be used as a secondary confirmation.

## 7. Cash Holdings

During periods of market stress (VIX above threshold), the strategy may hold up to 50% in cash equivalents.

The exact VIX threshold is determined by the Index Committee and may be adjusted.

## 8. Performance Calculation

Returns are calculated using the methodology described in Section 3 above, but note that some legacy systems may still reference the previous v1.5 calculation approach which used price returns rather than total returns.

## 9. Appendix - Historical Changes

- v1.0: Initial release
- v1.5: Added cash holding provisions
- v2.0: Changed to 11 GICS sectors
- v2.1: Current version (this document)

[Note: Change log may be incomplete. Contact the Index Team for full history.]
