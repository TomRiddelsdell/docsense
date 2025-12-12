"""Test script for term lineage extraction."""

import json
from src.infrastructure.semantic.definition_extractor import DefinitionExtractor
from src.infrastructure.semantic.lineage_extractor import LineageExtractor

# Sample document with definitions that reference each other
test_content = """
# Trading Algorithm Documentation

## Definitions

"Net Asset Value" means the total value of assets minus liabilities, calculated as of the close of business on each business day.

"Volatility" refers to the statistical measure of the dispersion of returns, typically measured as the standard deviation of returns over a 30 day period.

"Risk-Adjusted Return" means the return of an investment divided by the "Volatility" of that investment, expressed as a percentage.

"Sharpe Ratio" is defined as the "Risk-Adjusted Return" minus the risk-free rate, where the risk-free rate is typically 2.5%.

"Portfolio Value" means the sum of all positions multiplied by their respective market values as of the valuation date.
"""

def test_lineage_extraction():
    """Test that lineage is properly extracted."""

    # Initialize extractor
    extractor = DefinitionExtractor()

    # Extract definitions
    definitions = extractor.extract(test_content, "test-section")

    print(f"✓ Extracted {len(definitions)} definitions\n")

    # Print each definition with its lineage
    for defn in definitions:
        print(f"Term: {defn.term}")
        print(f"Definition: {defn.definition[:100]}...")

        if defn.lineage:
            print(f"  Lineage Information:")
            print(f"    - Is Computed: {defn.lineage.is_computed}")

            if defn.lineage.input_terms:
                print(f"    - Input Terms ({len(defn.lineage.input_terms)}):")
                for dep in defn.lineage.input_terms:
                    print(f"      • {dep.name} ({dep.dependency_type.value})")

            if defn.lineage.parameters:
                print(f"    - Parameters ({len(defn.lineage.parameters)}):")
                for param in defn.lineage.parameters:
                    print(f"      • {param.name} ({param.param_type})")
                    if param.units:
                        print(f"        Units: {param.units}")
                    if param.default_value is not None:
                        print(f"        Default: {param.default_value}")

            if defn.lineage.formula:
                print(f"    - Formula: {defn.lineage.formula}")

            if defn.lineage.computation_description:
                print(f"    - Computation: {defn.lineage.computation_description[:80]}...")

            if defn.lineage.conditions:
                print(f"    - Conditions: {len(defn.lineage.conditions)}")
        else:
            print("  No lineage information")

        print()

    # Test serialization
    print("\n" + "="*60)
    print("Testing Serialization")
    print("="*60 + "\n")

    for defn in definitions:
        # Serialize to dict
        defn_dict = defn.to_dict()

        # Verify lineage is in dict
        if defn.lineage:
            assert 'lineage' in defn_dict, "Lineage not in serialized dict"
            assert defn_dict['lineage'] is not None, "Lineage is None in dict"
            print(f"✓ {defn.term}: lineage serialized successfully")

            # Show serialized lineage
            if defn_dict['lineage'].get('input_terms'):
                print(f"  Input terms: {[t['name'] for t in defn_dict['lineage']['input_terms']]}")
            if defn_dict['lineage'].get('parameters'):
                print(f"  Parameters: {[p['name'] for p in defn_dict['lineage']['parameters']]}")

    print("\n" + "="*60)
    print("Testing Deserialization")
    print("="*60 + "\n")

    # Test round-trip serialization
    for defn in definitions:
        defn_dict = defn.to_dict()
        reconstructed = defn.__class__.from_dict(defn_dict)

        assert reconstructed.term == defn.term
        assert reconstructed.definition == defn.definition

        if defn.lineage:
            assert reconstructed.lineage is not None
            assert len(reconstructed.lineage.input_terms) == len(defn.lineage.input_terms)
            assert len(reconstructed.lineage.parameters) == len(defn.lineage.parameters)
            print(f"✓ {defn.term}: round-trip successful")
        else:
            assert reconstructed.lineage is None
            print(f"✓ {defn.term}: round-trip successful (no lineage)")

    print("\n" + "="*60)
    print("All Tests Passed! ✓")
    print("="*60)

if __name__ == "__main__":
    test_lineage_extraction()
