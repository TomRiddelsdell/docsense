# Policy Repository Templates

This directory contains JSON templates for Policy Repositories that can be imported into the Trading Algorithm Document Analyzer.

## Available Templates

### SEC Index Publishing (`sec-index-publishing.json`)

Regulatory requirements for index methodology documents submitted to the SEC. Covers:
- Methodology description (MUST)
- Component selection criteria (MUST)
- Rebalancing rules (MUST)
- Corporate action handling (SHOULD)
- Data sources (SHOULD)
- Governance structure (MAY)

### Internal Algorithm Standard (`internal-algo-standard.json`)

Internal documentation standards for quantitative trading algorithms. Covers:
- Algorithm overview (MUST)
- Signal generation (MUST)
- Risk management (MUST)
- Execution logic (SHOULD)
- Backtesting results (SHOULD)
- Data requirements (SHOULD)
- Dependencies and infrastructure (MAY)
- Version history (MAY)

## Template Structure

Each template is a JSON file with the following structure:

```json
{
  "name": "Repository Name",
  "description": "Description of the policy repository",
  "policies": [
    {
      "name": "Policy Name",
      "description": "What this policy checks",
      "requirement_type": "must|should|may",
      "validation_rules": [
        {
          "rule_type": "section_required|content_pattern|format_check|ai_evaluation",
          "pattern": "regex pattern",
          "error_message": "Error message if validation fails"
        }
      ],
      "ai_prompt_template": "Instructions for AI to evaluate this policy"
    }
  ]
}
```

## Requirement Types

- **MUST**: Mandatory requirement. Non-compliance results in a violation.
- **SHOULD**: Recommended. Non-compliance triggers a warning.
- **MAY**: Optional. Presence is noted but absence is acceptable.

## Validation Rule Types

- **section_required**: Checks if a section matching the pattern exists
- **content_pattern**: Searches for specific content patterns
- **format_check**: Validates document formatting
- **ai_evaluation**: Uses AI to evaluate compliance

## Creating Custom Templates

1. Copy an existing template as a starting point
2. Modify the name and description
3. Add, remove, or modify policies as needed
4. Ensure each policy has appropriate validation rules
5. Write clear AI prompt templates for nuanced evaluations

## Importing Templates

Templates can be imported via:
1. The Policy Repository management API (`POST /api/v1/policy-repositories/import`)
2. The admin interface in the frontend
3. Database seeding during deployment
