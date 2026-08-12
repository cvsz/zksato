# Broker Certification

This document outlines the architecture, risk engine features, and TFEX UAT test cases required for broker certification.

## Architecture
The trading system architecture is designed for high performance, low latency, and fault tolerance. Key components include:
- Market Data Gateway
- Order Management System (OMS)
- Risk Engine
- Strategy Engine

## Risk Engine Features
The risk engine enforces pre-trade and post-trade risk limits, including:
- Fat-finger checks
- Max order size limits
- Position limits
- Price banding and volatility controls

## TFEX UAT Test Cases
1. **Connectivity**: Verify login, logout, and heartbeat mechanisms.
2. **Order Submission**: Submit Limit, Market, and Stop orders.
3. **Modifications & Cancellations**: Amend order quantity/price, cancel existing orders.
4. **Risk Breaches**: Trigger fat-finger limits and position limit rejections.
5. **Drop Copy**: Ensure trade capture matches clearing system drop copies.
