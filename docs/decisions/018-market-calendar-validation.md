# ADR-018: Market Calendar Validation Framework

**Status**: Accepted  
**Date**: 2024-12-08  
**Priority**: Critical  
**Related**: [ADR-017](017-implementation-precision-specification.md), [ADR-014](014-semantic-intermediate-representation.md)

## Context

**Market calendars are identified as a particularly critical source of implementation issues**, especially when specifications involve:
- Relative dates ("previous 20 days", "last month", "6 months ago")
- Data sampling periods ("daily for the past year", "weekly returns")
- Trading day calculations ("next business day", "end of quarter")
- Holiday handling (market closures, half-days, early closes)
- Multi-market scenarios (different calendars for different exchanges)

Common issues that lead to implementation discrepancies:

### 1. Ambiguous Date References
```
❌ "Calculate using the previous 20 days of data"
   → Is this 20 calendar days or 20 trading days?
   → Which market calendar? NYSE? LSE? Multi-market?
   → How to handle holidays within the period?

❌ "Monthly rebalancing"
   → End of calendar month or end of trading month?
   → What if month-end is a holiday?
   → Use last trading day of month or first day of next month?
```

### 2. Data Sampling Ambiguity
```
❌ "Calculate daily returns for the past year"
   → 365 calendar days or 252 trading days?
   → Which calendar year (Jan-Dec) or rolling 12 months?
   → How to handle weekends and holidays?
   → What if data is missing for a trading day?
```

### 3. Relative Date Calculation
```
❌ "Previous business day"
   → Business day vs trading day (different concepts)
   → Which market's calendar?
   → How far back if multiple consecutive holidays?
```

### 4. Multi-Market Complexity
```
❌ "Use 3-month correlation between US and Japanese equities"
   → Different market calendars (NYSE vs TSE)
   → How to align dates when markets have different holidays?
   → Use only dates when both markets open?
   → Use all available data and interpolate?
```

These ambiguities lead to:
- **Silent errors**: Different implementations use different calendars, producing different results
- **Data alignment issues**: Mismatched dates across markets in correlation/regression calculations
- **Edge case failures**: Unexpected holidays break calculations
- **Testing difficulties**: Hard to validate without explicit calendar specifications

## Decision

We will implement a **Market Calendar Validation Framework** that:
1. Detects all calendar-dependent specifications
2. Validates calendar specifications are complete and unambiguous
3. Provides calendar-aware validation and computation
4. Supports multiple market calendars with proper alignment

### 1. Calendar Specification Format

All temporal specifications must include explicit calendar information:

```yaml
# Single-market specification
date_reference:
  type: relative_trading_days
  offset: -20  # negative = past
  calendar: NYSE
  description: "20 NYSE trading days prior to calculation date"
  
# Period specification  
period:
  type: trading_days
  length: 252
  calendar: NYSE
  end: calculation_date
  description: "252 NYSE trading days ending on calculation date"
  
# Sampling specification
sampling:
  frequency: daily
  period: 1_year
  calendar_type: trading_days
  calendar: NYSE
  alignment: end_of_day
  timezone: America/New_York
  
# Multi-market specification
date_reference:
  type: multi_market_alignment
  markets:
    - calendar: NYSE
      timezone: America/New_York
    - calendar: TSE
      timezone: Asia/Tokyo
  alignment_strategy: both_open  # or: any_open, primary_market
  primary_market: NYSE
```

### 2. Calendar Types and Standards

**Supported Calendar Types**:
- `trading_days`: Days when the market is open for trading
- `business_days`: Days when businesses are typically open (Mon-Fri, excluding public holidays)
- `calendar_days`: All days including weekends and holidays
- `settlement_days`: Days when trades settle (may differ from trading days)

**Standard Market Calendars**:
- NYSE (New York Stock Exchange)
- NASDAQ
- LSE (London Stock Exchange)
- TSE (Tokyo Stock Exchange)
- HKEX (Hong Kong Exchange)
- Eurex
- Custom (requires explicit holiday list)

**Calendar Data Sources**:
- Primary: pandas_market_calendars library
- Secondary: exchange-calendars library
- Fallback: explicit holiday lists in data contracts

### 3. Validation Rules

The framework validates:

#### Rule 1: Explicit Calendar Specification
```
❌ "previous 20 days"
✅ "previous 20 NYSE trading days"
✅ "previous 20 calendar days"
```

#### Rule 2: Unambiguous Date Offsets
```
❌ "last month"
✅ "previous calendar month (2023-11-01 to 2023-11-30)"
✅ "previous 21 NYSE trading days (approximately one month)"
```

#### Rule 3: Holiday Handling
```
✅ "If calculation date is not a trading day, use the previous trading day"
✅ "Skip non-trading days; require minimum 80% data availability"
✅ "If end-of-month is a holiday, use last trading day of month"
```

#### Rule 4: Timezone Specification
```
❌ "market close"
✅ "market close (16:00 America/New_York)"
✅ "market close (09:00 UTC, TSE)"
```

#### Rule 5: Data Alignment
```
✅ For multi-market: "Use only dates when both NYSE and TSE are open"
✅ For missing data: "Linear interpolation for up to 3 consecutive missing days"
✅ For weekends: "Carry forward Friday's value for Saturday and Sunday"
```

### 4. Validation Output

```json
{
  "calendar_validation": {
    "total_temporal_references": 15,
    "complete_specifications": 12,
    "incomplete_specifications": 3,
    "score": 0.80,
    "issues": [
      {
        "severity": "critical",
        "location": "section_2.3, line_42",
        "text": "Calculate using previous 20 days",
        "issue": "Calendar type not specified (trading vs calendar days)",
        "suggestion": "Specify: 'previous 20 NYSE trading days' or 'previous 20 calendar days'",
        "examples": [
          "2024-01-15 to 2024-12-08 (trading days, NYSE): 222 days",
          "2024-01-15 to 2024-12-08 (calendar days): 329 days"
        ]
      },
      {
        "severity": "high",
        "location": "section_3.1, line_67",
        "text": "monthly rebalancing",
        "issue": "End-of-month handling not specified",
        "suggestion": "Specify: 'rebalance on last NYSE trading day of each calendar month'",
        "edge_cases": [
          "December 2024: month-end is Tuesday 31st (trading day) → use 31st",
          "February 2025: month-end is Friday 28th (trading day) → use 28th",
          "May 2025: month-end is Saturday 31st (non-trading) → use Friday 30th?"
        ]
      },
      {
        "severity": "medium",
        "location": "section_4.2, line_103",
        "text": "3-month correlation between US and Japanese equities",
        "issue": "Multi-market date alignment not specified",
        "suggestion": "Specify alignment: 'Use only dates when both NYSE and TSE are open' or 'Use all available data with forward-fill for closures'",
        "impact": "Different alignments can produce different correlation values"
      }
    ]
  }
}
```

### 5. Calendar-Aware Computation

Provide utility functions for calendar computations:

```python
# In semantic_ir/calendar.py
from pandas_market_calendars import get_calendar

class MarketCalendar:
    """Calendar-aware date computation with validation"""
    
    def trading_days_between(
        self,
        start_date: date,
        end_date: date,
        calendar: str = "NYSE"
    ) -> int:
        """Count trading days between two dates"""
        cal = get_calendar(calendar)
        schedule = cal.schedule(start_date, end_date)
        return len(schedule)
    
    def add_trading_days(
        self,
        base_date: date,
        offset: int,
        calendar: str = "NYSE"
    ) -> date:
        """Add/subtract trading days from a date"""
        cal = get_calendar(calendar)
        valid_days = cal.valid_days(
            start_date=base_date - timedelta(days=abs(offset) * 2),
            end_date=base_date + timedelta(days=abs(offset) * 2)
        )
        # Find base_date position and offset
        try:
            idx = valid_days.get_loc(base_date)
            return valid_days[idx + offset]
        except KeyError:
            # base_date is not a trading day
            raise ValueError(f"{base_date} is not a {calendar} trading day")
    
    def is_trading_day(
        self,
        date: date,
        calendar: str = "NYSE"
    ) -> bool:
        """Check if a date is a trading day"""
        cal = get_calendar(calendar)
        return date in cal.valid_days(date, date)
    
    def align_multi_market(
        self,
        start_date: date,
        end_date: date,
        calendars: List[str],
        strategy: str = "all_open"
    ) -> List[date]:
        """Get dates when multiple markets are aligned"""
        if strategy == "all_open":
            # Intersection: dates when ALL markets are open
            valid_dates = None
            for cal_name in calendars:
                cal = get_calendar(cal_name)
                cal_valid = set(cal.valid_days(start_date, end_date))
                valid_dates = cal_valid if valid_dates is None else valid_dates & cal_valid
            return sorted(valid_dates)
        elif strategy == "any_open":
            # Union: dates when ANY market is open
            valid_dates = set()
            for cal_name in calendars:
                cal = get_calendar(cal_name)
                valid_dates |= set(cal.valid_days(start_date, end_date))
            return sorted(valid_dates)
        else:
            raise ValueError(f"Unknown alignment strategy: {strategy}")
```

### 6. Integration with Semantic IR

Extend semantic extraction to capture calendar specifications:

```python
# In domain/semantic/calendar_extractor.py

class CalendarExtractor:
    """Extract and validate calendar specifications from text"""
    
    PATTERNS = {
        "relative_days": r"(?:previous|last|past)\s+(\d+)\s+(days?|trading days?)",
        "period_spec": r"(\d+)[-\s](?:day|month|year)",
        "frequency": r"(daily|weekly|monthly|quarterly|annually)",
        "end_of_period": r"end of (?:day|month|quarter|year)",
        "market_names": r"(NYSE|NASDAQ|LSE|TSE|HKEX)",
    }
    
    def extract_calendar_refs(self, text: str) -> List[CalendarReference]:
        """Extract calendar references and validate completeness"""
        refs = []
        # Extract patterns
        # Validate against rules
        # Flag incomplete specifications
        # Generate suggestions
        return refs
```

### 7. AI Agent Prompts

Generate specific prompts for resolving calendar ambiguities:

```
The following specification contains ambiguous calendar references:

Text: "Calculate using the previous 20 days of data"

Ambiguities:
1. Calendar type: trading days or calendar days?
2. Market calendar: NYSE, LSE, TSE, or other?
3. Holiday handling: skip holidays or include all days?
4. Timezone: if intraday data, which timezone?

Context: This appears in a US equity strategy document.

Please provide complete calendar specification:
- Specify calendar type (trading_days/calendar_days)
- Specify market calendar (e.g., NYSE)
- Specify holiday handling approach
- Specify timezone if relevant

Example complete specification:
"Calculate using the previous 20 NYSE trading days (excluding weekends and 
NYSE holidays, using America/New_York timezone for intraday data)"
```

## Consequences

### Positive

- **Eliminates silent calendar errors**: All temporal references validated for calendar specifications
- **Bulletproof date calculations**: Calendar-aware utilities ensure correct date arithmetic
- **Multi-market support**: Proper handling of different market calendars with alignment strategies
- **Edge case handling**: Explicit specifications for holidays, weekends, month-ends
- **Reproducible results**: Same calendar specifications produce identical date ranges across implementations
- **Better testing**: Explicit calendars enable comprehensive edge case testing

### Negative

- **Increased specification verbosity**: Calendar specs add detail to documents
- **Learning curve**: Teams must learn calendar specification formats
- **Calendar data dependency**: Requires accurate calendar data for all supported markets
- **Maintenance**: Calendar data must be updated annually with holiday schedules

### Risks

- **Calendar data errors**: Incorrect holiday data could cause silent failures
- **Edge case complexity**: Some calendar scenarios may be extremely complex (e.g., three-market alignment with different business hours)
- **Historical data**: Historical calendar data may be incomplete for older periods

## Implementation

1. Create `domain/semantic/calendar.py` with `MarketCalendar` utility class
2. Create `domain/semantic/calendar_extractor.py` for pattern detection
3. Add calendar validation to `PrecisionValidator` (from ADR-017)
4. Integrate with Semantic IR as calendar metadata on temporal references
5. Create UI components for displaying calendar validation results
6. Add calendar specification templates to documentation
7. Generate calendar-specific AI agent prompts

**Dependencies**:
- pandas_market_calendars library (primary)
- exchange-calendars library (backup)

**Target**: Phase 12 in implementation plan (high priority after ADR-017)

**Testing Requirements**:
- Test with major market calendars (NYSE, LSE, TSE, HKEX)
- Test multi-year periods including leap years
- Test edge cases: consecutive holidays, year boundaries, DST transitions
- Test multi-market alignments with different holiday schedules
- Validate against known historical date ranges

## References

- [Enhancement Proposals](../analysis/vision-enhancement-proposals.md) - Section 1.3 (Temporal Semantics), Section 2.3 (Data Contracts)
- [ADR-017: Implementation Precision](017-implementation-precision-specification.md) - Parent framework
- [ADR-014: Semantic IR](014-semantic-intermediate-representation.md) - Semantic extraction base
- pandas_market_calendars: https://github.com/rsheftel/pandas_market_calendars
- exchange-calendars: https://github.com/gerrymanoim/exchange_calendars
