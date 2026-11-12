# zksato-risk

Risk engine, policies, and checks for the zksato trading platform.

## Contents

- **Engine**: `RiskEngine` - Deterministic pre-trade risk evaluation
- **Policies**: Declarative risk policies (TOML/YAML configurable)
- **Checks**: Composable risk checks for position, notional, market, portfolio
- **Approval**: Four-eyes approval workflow for live execution
- **Metrics**: Risk evaluation metrics and monitoring

## Installation

```bash
pip install -e packages/zksato-risk
```

## Usage

```python
from zksato_risk import (
    RiskEngine,
    create_default_policies,
    PolicyEngine,
    PositionLimitCheck,
    NotionalLimitCheck,
)

# Create risk engine with settings
engine = RiskEngine(settings)

# Or use policy-based approach
policies = create_default_policies(settings)
policy_engine = PolicyEngine(policies)

# Evaluate an order
decision = engine.evaluate(intent, context)
# or
decision = policy_engine.evaluate(intent, context)
```